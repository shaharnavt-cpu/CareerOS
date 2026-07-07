"""Lightweight single-worker queue for background Universal Listening."""

from __future__ import annotations

import logging
import queue
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.schemas.knowledge import DEMO_USER_ID
from app.schemas.listening import SourceSubmission
from app.services.document_adapters import (
    DocumentAdapterError,
    DocumentAdapterRegistry,
    RawDocument,
)
from app.services.document_detection import DocumentDetector
from app.services.listening import ListeningEngine
from app.services.listening_repository import ListeningRepository

logger = logging.getLogger(__name__)


class ListeningJobStage(StrEnum):
    """User-facing stages shared by the API and composer."""

    QUEUED = "QUEUED"
    READING = "READING"
    EXTRACTING_EVIDENCE = "EXTRACTING_EVIDENCE"
    COMPARING_SOURCES = "COMPARING_SOURCES"
    PREPARING_PROPOSALS = "PREPARING_PROPOSALS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ProcessingResult:
    """Safe identifiers and metadata returned after staged persistence."""

    source_id: uuid.UUID
    source_type: str
    document_type: str
    detection_confidence: float
    evidence_count: int


ProgressReporter = Callable[[ListeningJobStage, int, str], None]


class DocumentProcessor(Protocol):
    """Queue processing boundary, injectable for deterministic tests."""

    def __call__(
        self, document: RawDocument, report: ProgressReporter
    ) -> ProcessingResult:
        """Extract, detect, listen, fuse, and stage one document."""


@dataclass
class ListeningJob:
    """Mutable in-memory state for one queued source."""

    id: uuid.UUID
    document: RawDocument
    stage: ListeningJobStage = ListeningJobStage.QUEUED
    progress: int = 0
    message: str = "Waiting to be heard"
    attempt: int = 1
    source_id: uuid.UUID | None = None
    source_type: str | None = None
    document_type: str | None = None
    detection_confidence: float | None = None
    evidence_count: int = 0
    error_code: str | None = None
    created_at: datetime = datetime.min.replace(tzinfo=UTC)
    updated_at: datetime = datetime.min.replace(tzinfo=UTC)

    def __post_init__(self) -> None:
        now = datetime.now(UTC)
        if self.created_at == datetime.min.replace(tzinfo=UTC):
            self.created_at = now
        if self.updated_at == datetime.min.replace(tzinfo=UTC):
            self.updated_at = now


class ListeningQueue:
    """FIFO queue that processes exactly one source at a time."""

    def __init__(self, processor: DocumentProcessor, *, autostart: bool = True) -> None:
        self._processor = processor
        self._pending: queue.Queue[uuid.UUID | None] = queue.Queue()
        self._jobs: dict[uuid.UUID, ListeningJob] = {}
        self._lock = threading.RLock()
        self._worker: threading.Thread | None = None
        if autostart:
            self.start()

    def start(self) -> None:
        with self._lock:
            if self._worker and self._worker.is_alive():
                return
            self._worker = threading.Thread(
                target=self._work,
                name="careeros-listening-worker",
                daemon=True,
            )
            self._worker.start()

    def enqueue(self, document: RawDocument) -> ListeningJob:
        job = ListeningJob(id=uuid.uuid4(), document=document)
        with self._lock:
            self._jobs[job.id] = job
        self._pending.put(job.id)
        return self.get(job.id)

    def get(self, job_id: uuid.UUID) -> ListeningJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return self._snapshot(job)

    def list(self) -> list[ListeningJob]:
        with self._lock:
            return [
                self._snapshot(job)
                for job in sorted(
                    self._jobs.values(), key=lambda item: item.created_at, reverse=True
                )
            ]

    def retry(self, job_id: uuid.UUID) -> ListeningJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            if job.stage is not ListeningJobStage.FAILED:
                raise ValueError("Only failed listening jobs can be retried.")
            job.stage = ListeningJobStage.QUEUED
            job.progress = 0
            job.message = "Queued for another listen"
            job.attempt += 1
            job.error_code = None
            job.updated_at = datetime.now(UTC)
        self._pending.put(job_id)
        return self.get(job_id)

    def join(self, timeout: float = 5.0) -> bool:
        """Wait for test or shutdown coordination without blocking indefinitely."""

        done = threading.Event()

        def wait_for_queue() -> None:
            self._pending.join()
            done.set()

        threading.Thread(target=wait_for_queue, daemon=True).start()
        return done.wait(timeout)

    def shutdown(self) -> None:
        self._pending.put(None)
        worker = self._worker
        if worker:
            worker.join(timeout=2)

    def _work(self) -> None:
        while True:
            job_id = self._pending.get()
            try:
                if job_id is None:
                    return
                self._process(job_id)
            finally:
                self._pending.task_done()

    def _process(self, job_id: uuid.UUID) -> None:
        document = self.get(job_id).document

        def report(stage: ListeningJobStage, progress: int, message: str) -> None:
            self._update(job_id, stage, progress, message)

        try:
            result = self._processor(document, report)
            with self._lock:
                job = self._jobs[job_id]
                job.source_id = result.source_id
                job.source_type = result.source_type
                job.document_type = result.document_type
                job.detection_confidence = result.detection_confidence
                job.evidence_count = result.evidence_count
            self._update(
                job_id,
                ListeningJobStage.COMPLETE,
                100,
                "Listening complete — ready for your review",
            )
        except DocumentAdapterError as exc:
            self._fail(job_id, exc.code, exc.user_message)
        except Exception:
            logger.exception("Unexpected listening failure for job %s", job_id)
            self._fail(
                job_id,
                "EXTRACTION_FAILED",
                "CareerOS could not finish listening to this file. Try exporting a "
                "fresh copy and attach it again.",
            )

    def _update(
        self, job_id: uuid.UUID, stage: ListeningJobStage, progress: int, message: str
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.stage = stage
            job.progress = progress
            job.message = message
            job.updated_at = datetime.now(UTC)

    def _fail(self, job_id: uuid.UUID, code: str, message: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.stage = ListeningJobStage.FAILED
            job.progress = 100
            job.message = message
            job.error_code = code
            job.updated_at = datetime.now(UTC)

    @staticmethod
    def _snapshot(job: ListeningJob) -> ListeningJob:
        return ListeningJob(**job.__dict__)


class UniversalListeningProcessor:
    """Production processor that reuses the existing listening persistence seam."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        adapters: DocumentAdapterRegistry | None = None,
        detector: DocumentDetector | None = None,
        engine: ListeningEngine | None = None,
        repository: ListeningRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._adapters = adapters or DocumentAdapterRegistry()
        self._detector = detector or DocumentDetector()
        self._engine = engine or ListeningEngine()
        self._repository = repository or ListeningRepository()

    def __call__(
        self, document: RawDocument, report: ProgressReporter
    ) -> ProcessingResult:
        report(ListeningJobStage.READING, 15, f"Reading {document.filename}")
        extracted = self._adapters.extract(document)
        detection = self._detector.detect(document.filename, extracted.text)
        report(
            ListeningJobStage.EXTRACTING_EVIDENCE,
            45,
            f"Listening as {detection.document_type.value.replace('_', ' ').title()}",
        )
        source, evidence, clusters = self._engine.listen(
            SourceSubmission(
                source_type=detection.source_type,
                label=Path(document.filename).stem,
                raw_text=extracted.text,
                original_filename=document.filename,
                media_type=document.media_type,
                metadata={
                    **extracted.metadata,
                    "document_format": extracted.format,
                    "document_type": detection.document_type.value,
                    "detection_confidence": detection.confidence,
                    "detection_reasons": list(detection.reasons),
                    "document_adapter_version": extracted.adapter_version,
                },
            ),
            DEMO_USER_ID,
        )
        report(
            ListeningJobStage.COMPARING_SOURCES,
            70,
            "Comparing this evidence with what CareerOS already heard",
        )
        with self._session_factory() as session:
            summary = self._repository.persist_ingestion(
                session, source, evidence, clusters
            )
        report(
            ListeningJobStage.PREPARING_PROPOSALS,
            90,
            "Preparing evidence-backed proposals",
        )
        return ProcessingResult(
            source_id=summary.id,
            source_type=summary.source_type.value,
            document_type=detection.document_type.value,
            detection_confidence=detection.confidence,
            evidence_count=summary.evidence_count,
        )
