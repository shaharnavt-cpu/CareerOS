"""PostgreSQL regression coverage for idempotent listening persistence."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.db.session import SessionLocal, engine
from app.models import (
    ListeningClusterMember,
    ListeningEvidence,
    ListeningEvidenceCluster,
    ListeningProposalEvidenceLink,
    ListeningSource,
    User,
)
from app.services.document_adapters import RawDocument
from app.services.listening_queue import (
    JobStatus,
    ListeningQueue,
    PersistenceStatus,
    PipelineStage,
    UniversalListeningProcessor,
)
from app.services.listening_repository import ListeningRepository


class CommitThenDisconnectRepository(ListeningRepository):
    """Simulate an ambiguous connection loss after PostgreSQL committed."""

    def __init__(self) -> None:
        self.attempts = 0

    def persist_ingestion(self, session, source, evidence, clusters):
        summary = super().persist_ingestion(session, source, evidence, clusters)
        self.attempts += 1
        if self.attempts == 1:
            raise OperationalError(
                "commit",
                {},
                ConnectionError("connection dropped after commit"),
            )
        return summary


def _require_postgres() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")


def _remove_test_user(user_id: uuid.UUID) -> None:
    with SessionLocal.begin() as session:
        for model in (
            ListeningProposalEvidenceLink,
            ListeningClusterMember,
            ListeningEvidenceCluster,
            ListeningEvidence,
            ListeningSource,
        ):
            session.execute(delete(model).where(model.user_id == user_id))
        session.execute(delete(User).where(User.id == user_id))


def test_duplicate_evidence_and_post_commit_retry_are_idempotent() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    repository = CommitThenDisconnectRepository()
    listening_queue = ListeningQueue(
        UniversalListeningProcessor(
            SessionLocal,
            repository=repository,
            user_id=user_id,
        )
    )

    try:
        queued = listening_queue.enqueue(
            RawDocument(
                "resume.txt",
                b"Experience\nEngineer at Acme\nEngineer at Acme",
                "text/plain",
            )
        )
        assert listening_queue.join()

        failed = listening_queue.get(queued.id)
        assert failed.status is JobStatus.FAILED
        assert failed.current_stage is PipelineStage.PERSIST_EVIDENCE
        assert failed.persistence_status is PersistenceStatus.FAILED
        assert failed.failure is not None
        assert failed.failure.code == "DATABASE_UNAVAILABLE"

        listening_queue.retry(queued.id)
        assert listening_queue.join()

        recovered = listening_queue.get(queued.id)
        assert recovered.status is JobStatus.COMPLETE
        assert recovered.persistence_status is PersistenceStatus.SAVED
        assert recovered.source_id is not None
        assert recovered.retry_count == 1
        assert repository.attempts == 2

        with SessionLocal() as session:
            source_count = session.scalar(
                select(func.count(ListeningSource.id)).where(
                    ListeningSource.user_id == user_id
                )
            )
            rows = session.execute(
                select(
                    ListeningEvidence.source_id,
                    ListeningEvidence.excerpt_hash,
                ).where(ListeningEvidence.user_id == user_id)
            ).all()

        assert source_count == 1
        assert rows
        assert len(rows) == len(set(rows))
        assert {source_id for source_id, _ in rows} == {recovered.source_id}
        assert recovered.evidence_count == len(rows)
        assert recovered.evidence_count < len(recovered.artifacts.evidence)
    finally:
        listening_queue.shutdown()
        _remove_test_user(user_id)
