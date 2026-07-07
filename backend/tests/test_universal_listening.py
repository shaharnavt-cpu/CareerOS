"""Universal Listening adapters, detection, queue, and progress API tests."""

from __future__ import annotations

import threading
import uuid
from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.api.listening import get_listening_queue
from app.main import app
from app.services.document_adapters import (
    DocumentAdapterError,
    DocxDocumentAdapter,
    PdfDocumentAdapter,
    RawDocument,
)
from app.services.document_detection import DocumentDetector, DocumentType
from app.services.listening_queue import (
    ListeningJobStage,
    ListeningQueue,
    ProcessingResult,
)


def make_pdf(text: str, *, password: str | None = None) -> bytes:
    """Create a small text PDF without adding a test-only rendering dependency."""

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    safe_text = text.replace("(", "[").replace(")", "]")
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({safe_text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    if password:
        writer.encrypt(password)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def make_docx() -> bytes:
    document = Document()
    document.add_heading("Professional Experience", level=1)
    document.add_paragraph("Software Engineer at Acme")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Skills"
    table.rows[0].cells[1].text = "Python, SQL"
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def test_pdf_ingestion_extracts_page_text_and_metadata() -> None:
    result = PdfDocumentAdapter().extract(
        RawDocument("resume.pdf", make_pdf("Resume Skills Python"), "application/pdf")
    )

    assert "Resume Skills Python" in result.text
    assert result.metadata["page_count"] == 1
    assert result.adapter_version == "pdf-adapter-v1"


def test_docx_ingestion_extracts_paragraphs_and_tables() -> None:
    result = DocxDocumentAdapter().extract(
        RawDocument(
            "career.docx",
            make_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    )

    assert "Software Engineer at Acme" in result.text
    assert "Skills | Python, SQL" in result.text
    assert result.metadata["table_count"] == 1


def test_password_protected_pdf_has_actionable_error() -> None:
    with pytest.raises(DocumentAdapterError) as error:
        PdfDocumentAdapter().extract(
            RawDocument("locked.pdf", make_pdf("Private", password="secret"))
        )

    assert error.value.code == "PASSWORD_PROTECTED_PDF"
    assert "Remove the password" in error.value.user_message


@pytest.mark.parametrize(
    ("filename", "text", "expected"),
    [
        ("resume.pdf", "Skills Education Work Experience", DocumentType.RESUME),
        (
            "record.pdf",
            "Official Transcript Cumulative GPA Credit Hours",
            DocumentType.TRANSCRIPT,
        ),
        (
            "role.txt",
            "Job Description Responsibilities Qualifications Requirements",
            DocumentType.JOB_DESCRIPTION,
        ),
        (
            "award.docx",
            "Certificate awarded to Alex, credential ID 123",
            DocumentType.CERTIFICATE,
        ),
        (
            "paper.pdf",
            "Abstract Introduction Methodology References",
            DocumentType.RESEARCH_PAPER,
        ),
        ("work.pdf", "Portfolio Selected Work Case Study", DocumentType.PORTFOLIO),
        ("notes.txt", "Met Pat at the conference", DocumentType.GENERIC_DOCUMENT),
    ],
)
def test_document_detection(filename: str, text: str, expected: DocumentType) -> None:
    detection = DocumentDetector().detect(filename, text)

    assert detection.document_type is expected
    assert detection.reasons
    assert 0 <= detection.confidence <= 1


def test_queue_is_fifo_and_reports_progress() -> None:
    processed: list[str] = []
    first_started = threading.Event()
    release_first = threading.Event()

    def processor(document, report):
        report(ListeningJobStage.READING, 15, "Reading")
        processed.append(document.filename)
        if document.filename == "first.txt":
            first_started.set()
            release_first.wait(timeout=2)
        report(ListeningJobStage.PREPARING_PROPOSALS, 90, "Preparing")
        return ProcessingResult(
            source_id=uuid.uuid4(),
            source_type="RESUME",
            document_type="RESUME",
            detection_confidence=0.9,
            evidence_count=2,
        )

    listening_queue = ListeningQueue(processor)
    first = listening_queue.enqueue(RawDocument("first.txt", b"first"))
    second = listening_queue.enqueue(RawDocument("second.txt", b"second"))
    assert first_started.wait(timeout=2)
    assert listening_queue.get(second.id).stage is ListeningJobStage.QUEUED
    release_first.set()
    assert listening_queue.join()

    assert processed == ["first.txt", "second.txt"]
    assert listening_queue.get(first.id).stage is ListeningJobStage.COMPLETE
    assert listening_queue.get(second.id).progress == 100
    listening_queue.shutdown()


def test_failed_queue_job_can_be_retried() -> None:
    attempts = 0

    def processor(document, report):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise DocumentAdapterError(
                "CORRUPTED_PDF", "Export a fresh PDF and try again."
            )
        report(ListeningJobStage.READING, 20, "Reading")
        return ProcessingResult(
            source_id=uuid.uuid4(),
            source_type="RESUME",
            document_type="RESUME",
            detection_confidence=0.9,
            evidence_count=1,
        )

    listening_queue = ListeningQueue(processor)
    job = listening_queue.enqueue(RawDocument("resume.pdf", b"pdf"))
    assert listening_queue.join()
    assert listening_queue.get(job.id).stage is ListeningJobStage.FAILED
    assert listening_queue.get(job.id).error_code == "CORRUPTED_PDF"

    retried = listening_queue.retry(job.id)
    assert retried.attempt == 2
    assert listening_queue.join()
    assert listening_queue.get(job.id).stage is ListeningJobStage.COMPLETE
    listening_queue.shutdown()


def test_multiple_upload_and_progress_endpoints() -> None:
    def processor(document, report):
        report(ListeningJobStage.EXTRACTING_EVIDENCE, 50, "Extracting")
        return ProcessingResult(
            source_id=uuid.uuid4(),
            source_type="GENERIC_DOCUMENT",
            document_type="GENERIC_DOCUMENT",
            detection_confidence=0.5,
            evidence_count=1,
        )

    listening_queue = ListeningQueue(processor)
    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_listening_queue] = lambda: listening_queue
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/listening/uploads",
                files=[
                    ("files", ("one.txt", b"one", "text/plain")),
                    ("files", ("two.md", b"two", "text/markdown")),
                ],
            )
            assert response.status_code == 202
            assert len(response.json()["jobs"]) == 2
            assert listening_queue.join()

            jobs = client.get("/api/listening/jobs")
            assert jobs.status_code == 200
            assert {job["stage"] for job in jobs.json()} == {"COMPLETE"}
            job_id = jobs.json()[0]["id"]
            progress = client.get(f"/api/listening/jobs/{job_id}")
            assert progress.json()["progress"] == 100
            assert progress.json()["source_id"]
    finally:
        app.dependency_overrides = original
        listening_queue.shutdown()
