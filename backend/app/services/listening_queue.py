"""Resumable, observable single-worker queue for Universal Listening."""

from __future__ import annotations

import asyncio
import copy
import logging
import queue
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.schemas.knowledge import DEMO_USER_ID, KnowledgeProposal
from app.schemas.listening import (
    EvidenceCluster,
    EvidenceObject,
    NormalizedListeningSource,
    SourceSubmission,
)
from app.services.database_health import (
    DatabaseHealthMonitor,
    classify_database_failure,
    get_database_health,
)
from app.services.document_adapters import (
    DocumentAdapterError,
    DocumentAdapterRegistry,
    ExtractedDocument,
    RawDocument,
)
from app.services.document_detection import DocumentDetection, DocumentDetector
from app.services.listening import ListeningEngine, ListeningReasoningBridge
from app.services.listening_repository import ListeningRepository
from app.services.llm import ReasoningProviderError
from app.services.proposals import ReasoningValidationError

logger = logging.getLogger(__name__)


class PipelineStage(StrEnum):
    """Explicit Universal Listening stages in execution order."""

    UPLOAD = "UPLOAD"
    DETECT_DOCUMENT_TYPE = "DETECT_DOCUMENT_TYPE"
    PARSE_DOCUMENT = "PARSE_DOCUMENT"
    EXTRACT_TEXT = "EXTRACT_TEXT"
    CREATE_EVIDENCE = "CREATE_EVIDENCE"
    PERSIST_EVIDENCE = "PERSIST_EVIDENCE"
    COMPARE_KNOWLEDGE = "COMPARE_KNOWLEDGE"
    GENERATE_PROPOSALS = "GENERATE_PROPOSALS"
    COMPLETE = "COMPLETE"


PIPELINE_STAGES = list(PipelineStage)


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class StageStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class PersistenceStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    SAVING = "SAVING"
    SAVED = "SAVED"
    FAILED = "FAILED"


@dataclass
class StageTiming:
    stage: PipelineStage
    status: StageStatus = StageStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    message: str = "Waiting"


@dataclass
class JobFailure:
    code: str
    friendly_message: str
    developer_message: str
    exception_type: str
    stack_trace: str
    stage: PipelineStage
    retryable: bool
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ListeningArtifacts:
    """In-memory checkpoint retained across persistence retries."""

    detected_format: str | None = None
    extracted: ExtractedDocument | None = None
    detection: DocumentDetection | None = None
    normalized_source: NormalizedListeningSource | None = None
    evidence: list[EvidenceObject] = field(default_factory=list)
    source_clusters: list[EvidenceCluster] = field(default_factory=list)
    compared_clusters: list[EvidenceCluster] = field(default_factory=list)
    proposal_links_persisted: bool = False


@dataclass(frozen=True)
class ProcessingResult:
    source_id: uuid.UUID
    source_type: str
    document_type: str
    detection_confidence: float
    evidence_count: int
    proposals: list[KnowledgeProposal] = field(default_factory=list)


ProgressReporter = Callable[[PipelineStage, str], None]


class DocumentProcessor(Protocol):
    def __call__(self, job: ListeningJob, report: ProgressReporter) -> ProcessingResult:
        """Continue a job from its latest successful in-memory checkpoint."""


@dataclass
class ListeningJob:
    id: uuid.UUID
    document: RawDocument
    status: JobStatus = JobStatus.QUEUED
    current_stage: PipelineStage = PipelineStage.UPLOAD
    message: str = "Uploaded and waiting to be heard"
    attempt: int = 1
    source_id: uuid.UUID | None = None
    source_type: str | None = None
    document_type: str | None = None
    detection_confidence: float | None = None
    extracted_character_count: int = 0
    evidence_count: int = 0
    persistence_status: PersistenceStatus = PersistenceStatus.NOT_STARTED
    proposals: list[KnowledgeProposal] = field(default_factory=list)
    failure: JobFailure | None = None
    artifacts: ListeningArtifacts = field(default_factory=ListeningArtifacts)
    stage_timings: dict[PipelineStage, StageTiming] = field(default_factory=dict)
    developer_logs: list[dict[str, object]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @property
    def retry_count(self) -> int:
        return self.attempt - 1

    @property
    def elapsed_ms(self) -> float:
        end = self.completed_at or datetime.now(UTC)
        return round((end - self.created_at).total_seconds() * 1000, 2)


class ListeningQueue:
    """FIFO queue that keeps successful pre-persistence work available for retry."""

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
        now = datetime.now(UTC)
        timings = {stage: StageTiming(stage=stage) for stage in PIPELINE_STAGES}
        timings[PipelineStage.UPLOAD] = StageTiming(
            stage=PipelineStage.UPLOAD,
            status=StageStatus.COMPLETE,
            started_at=now,
            completed_at=now,
            duration_ms=0,
            message="Upload received",
        )
        job = ListeningJob(
            id=uuid.uuid4(),
            document=document,
            current_stage=PipelineStage.DETECT_DOCUMENT_TYPE,
            stage_timings=timings,
            created_at=now,
            updated_at=now,
        )
        job.developer_logs.append(self._log("UPLOAD", "Upload received", attempt=1))
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
            if job.status is not JobStatus.FAILED:
                raise ValueError("Only failed listening jobs can be retried.")
            resume_stage = self._resume_stage(job)
            resume_index = PIPELINE_STAGES.index(resume_stage)
            for stage in PIPELINE_STAGES[resume_index:]:
                job.stage_timings[stage] = StageTiming(stage=stage)
            job.status = JobStatus.QUEUED
            job.current_stage = resume_stage
            job.message = f"Queued to resume at {resume_stage.value}"
            job.attempt += 1
            job.failure = None
            job.completed_at = None
            job.updated_at = datetime.now(UTC)
            job.developer_logs.append(
                self._log(
                    "RETRY",
                    "Job queued for retry from checkpoint",
                    attempt=job.attempt,
                    resume_stage=resume_stage.value,
                )
            )
        self._pending.put(job_id)
        return self.get(job_id)

    def join(self, timeout: float = 5.0) -> bool:
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
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.ACTIVE

        def report(stage: PipelineStage, message: str) -> None:
            self._transition(job_id, stage, message)

        try:
            result = self._processor(job, report)
        except OperationalError as error:
            failure = classify_database_failure(error)
            get_database_health().mark_failure(failure)
            self._fail(
                job_id,
                failure.code,
                failure.friendly_message,
                failure.developer_message,
                failure.exception_type,
                failure.stack_trace,
                retryable=True,
            )
            return
        except DocumentAdapterError as error:
            code = error.code
            if code not in {"EMPTY_DOCUMENT", "NO_TEXT_FOUND", "UNSUPPORTED_FILE"}:
                code = "PARSER_FAILED"
            self._fail_from_exception(
                job_id, code, error.user_message, error, retryable=True
            )
            return
        except ReasoningProviderError as error:
            self._fail_from_exception(
                job_id,
                "REASONING_FAILURE",
                "CareerOS could not complete reasoning for this source. Your evidence "
                "is saved; retry when the reasoning provider is available.",
                error,
                retryable=True,
            )
            return
        except ReasoningValidationError as error:
            self._fail_from_exception(
                job_id,
                "PROPOSAL_FAILURE",
                "CareerOS could not validate proposals from this source. Your evidence "
                "is saved and can be retried.",
                error,
                retryable=True,
            )
            return
        except Exception as error:
            logger.exception("Unexpected listening failure for job %s", job_id)
            stage = self._jobs[job_id].current_stage
            code = (
                "PARSER_FAILED"
                if stage
                in {
                    PipelineStage.DETECT_DOCUMENT_TYPE,
                    PipelineStage.PARSE_DOCUMENT,
                    PipelineStage.EXTRACT_TEXT,
                    PipelineStage.CREATE_EVIDENCE,
                }
                else "PROPOSAL_FAILURE"
                if stage is PipelineStage.GENERATE_PROPOSALS
                else "REASONING_FAILURE"
            )
            self._fail_from_exception(
                job_id,
                code,
                "CareerOS stopped at this stage, but completed work remains available "
                "for a retry.",
                error,
                retryable=True,
            )
            return

        with self._lock:
            job.source_id = result.source_id
            job.source_type = result.source_type
            job.document_type = result.document_type
            job.detection_confidence = result.detection_confidence
            job.evidence_count = result.evidence_count
            job.proposals = result.proposals
        self._transition(job_id, PipelineStage.COMPLETE, "Listening complete")
        with self._lock:
            job.status = JobStatus.COMPLETE
            job.completed_at = datetime.now(UTC)
            job.updated_at = job.completed_at
            job.developer_logs.append(
                self._log(
                    "COMPLETE",
                    "Pipeline completed",
                    attempt=job.attempt,
                    elapsed_ms=job.elapsed_ms,
                )
            )

    def _transition(
        self, job_id: uuid.UUID, stage: PipelineStage, message: str
    ) -> None:
        now = datetime.now(UTC)
        with self._lock:
            job = self._jobs[job_id]
            previous = job.stage_timings[job.current_stage]
            if previous.status is StageStatus.ACTIVE:
                previous.status = StageStatus.COMPLETE
                previous.completed_at = now
                if previous.started_at:
                    previous.duration_ms = round(
                        (now - previous.started_at).total_seconds() * 1000, 2
                    )
            current = job.stage_timings[stage]
            current.status = (
                StageStatus.COMPLETE
                if stage is PipelineStage.COMPLETE
                else StageStatus.ACTIVE
            )
            current.started_at = current.started_at or now
            current.message = message
            if stage is PipelineStage.COMPLETE:
                current.completed_at = now
                current.duration_ms = 0
            job.current_stage = stage
            job.message = message
            job.updated_at = now
            job.developer_logs.append(
                self._log(
                    stage.value,
                    message,
                    attempt=job.attempt,
                    elapsed_ms=job.elapsed_ms,
                )
            )

    def _fail_from_exception(
        self,
        job_id: uuid.UUID,
        code: str,
        friendly_message: str,
        error: BaseException,
        *,
        retryable: bool,
    ) -> None:
        self._fail(
            job_id,
            code,
            friendly_message,
            str(error),
            type(error).__name__,
            "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            ),
            retryable=retryable,
        )

    def _fail(
        self,
        job_id: uuid.UUID,
        code: str,
        friendly_message: str,
        developer_message: str,
        exception_type: str,
        stack_trace: str,
        *,
        retryable: bool,
    ) -> None:
        now = datetime.now(UTC)
        with self._lock:
            job = self._jobs[job_id]
            timing = job.stage_timings[job.current_stage]
            timing.status = StageStatus.FAILED
            timing.completed_at = now
            if timing.started_at:
                timing.duration_ms = round(
                    (now - timing.started_at).total_seconds() * 1000, 2
                )
            if job.current_stage is PipelineStage.PERSIST_EVIDENCE:
                job.persistence_status = PersistenceStatus.FAILED
            job.status = JobStatus.FAILED
            job.message = friendly_message
            job.failure = JobFailure(
                code=code,
                friendly_message=friendly_message,
                developer_message=developer_message,
                exception_type=exception_type,
                stack_trace=stack_trace,
                stage=job.current_stage,
                retryable=retryable,
            )
            job.completed_at = now
            job.updated_at = now
            job.developer_logs.append(
                self._log(
                    "FAILURE",
                    friendly_message,
                    attempt=job.attempt,
                    stage=job.current_stage.value,
                    error_code=code,
                )
            )

    @staticmethod
    def _resume_stage(job: ListeningJob) -> PipelineStage:
        if job.persistence_status is not PersistenceStatus.SAVED:
            if job.artifacts.normalized_source and job.artifacts.evidence:
                return PipelineStage.PERSIST_EVIDENCE
            return PipelineStage.DETECT_DOCUMENT_TYPE
        if not job.artifacts.compared_clusters:
            return PipelineStage.COMPARE_KNOWLEDGE
        return PipelineStage.GENERATE_PROPOSALS

    @staticmethod
    def _snapshot(job: ListeningJob) -> ListeningJob:
        snapshot = copy.copy(job)
        snapshot.stage_timings = copy.deepcopy(job.stage_timings)
        snapshot.developer_logs = copy.deepcopy(job.developer_logs)
        snapshot.proposals = list(job.proposals)
        return snapshot

    @staticmethod
    def _log(event: str, message: str, **details: object) -> dict[str, object]:
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "message": message,
            **details,
        }


class UniversalListeningProcessor:
    """Execute each stage while retaining pre-database artifacts in memory."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        adapters: DocumentAdapterRegistry | None = None,
        detector: DocumentDetector | None = None,
        engine: ListeningEngine | None = None,
        repository: ListeningRepository | None = None,
        reasoning_bridge: ListeningReasoningBridge | None = None,
        database_health: DatabaseHealthMonitor | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._adapters = adapters or DocumentAdapterRegistry()
        self._detector = detector or DocumentDetector()
        self._engine = engine or ListeningEngine()
        self._repository = repository or ListeningRepository()
        self._reasoning_bridge = reasoning_bridge
        self._database_health = database_health or get_database_health()

    def __call__(self, job: ListeningJob, report: ProgressReporter) -> ProcessingResult:
        artifacts = job.artifacts
        if artifacts.normalized_source is None or not artifacts.evidence:
            report(
                PipelineStage.DETECT_DOCUMENT_TYPE,
                f"{job.document.extension.removeprefix('.').upper()} detected",
            )
            self._adapters.validate(job.document)
            artifacts.detected_format = job.document.extension.removeprefix(".").upper()

            report(PipelineStage.PARSE_DOCUMENT, f"Parsing {job.document.filename}")
            extracted = self._adapters.extract(job.document)
            artifacts.extracted = extracted

            report(PipelineStage.EXTRACT_TEXT, "Text extracted")
            job.extracted_character_count = len(extracted.text)
            detection = self._detector.detect(job.document.filename, extracted.text)
            artifacts.detection = detection
            job.document_type = detection.document_type.value
            job.detection_confidence = detection.confidence

            report(PipelineStage.CREATE_EVIDENCE, "Creating evidence objects")
            source, evidence, clusters = self._engine.listen(
                SourceSubmission(
                    source_type=detection.source_type,
                    label=Path(job.document.filename).stem,
                    raw_text=extracted.text,
                    original_filename=job.document.filename,
                    media_type=job.document.media_type,
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
            artifacts.normalized_source = source
            artifacts.evidence = evidence
            artifacts.source_clusters = clusters
            job.evidence_count = len(evidence)

        source = artifacts.normalized_source
        detection = artifacts.detection
        if source is None or detection is None:
            raise RuntimeError("Listening checkpoint is incomplete.")

        if job.persistence_status is not PersistenceStatus.SAVED:
            report(PipelineStage.PERSIST_EVIDENCE, "Saving evidence to Career Memory")
            job.persistence_status = PersistenceStatus.SAVING
            started = time.perf_counter()
            with self._session_factory() as session:
                summary = self._repository.persist_ingestion(
                    session, source, artifacts.evidence, artifacts.source_clusters
                )
            job.persistence_status = PersistenceStatus.SAVED
            self._database_health.mark_available(started=started)
            job.source_id = summary.id
            job.source_type = summary.source_type.value
            job.evidence_count = summary.evidence_count

        if not artifacts.compared_clusters:
            report(
                PipelineStage.COMPARE_KNOWLEDGE,
                "Comparing with existing career evidence",
            )
            with self._session_factory() as session:
                all_evidence = self._repository.list_evidence(session)
                artifacts.compared_clusters = self._engine.fuse(all_evidence)
                self._repository.persist_clusters(
                    session, DEMO_USER_ID, artifacts.compared_clusters
                )

        report(PipelineStage.GENERATE_PROPOSALS, "Generating knowledge proposals")
        proposals = job.proposals
        if not proposals:
            if self._reasoning_bridge is None:
                proposals = []
            else:
                proposal_response = asyncio.run(
                    self._reasoning_bridge.generate(artifacts.compared_clusters, [])
                )
                proposals = proposal_response.proposals
                job.proposals = proposals
        if proposals and not artifacts.proposal_links_persisted:
            with self._session_factory() as session:
                self._repository.persist_proposal_links(
                    session,
                    DEMO_USER_ID,
                    proposals,
                    artifacts.compared_clusters,
                )
            artifacts.proposal_links_persisted = True

        return ProcessingResult(
            source_id=source.id,
            source_type=detection.source_type.value,
            document_type=detection.document_type.value,
            detection_confidence=detection.confidence,
            evidence_count=len(artifacts.evidence),
            proposals=proposals,
        )
