"""Persistence boundary for non-canonical listening data."""

from __future__ import annotations

import hashlib
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ListeningClusterMember,
    ListeningEvidence,
    ListeningEvidenceCluster,
    ListeningProposalEvidenceLink,
    ListeningSource,
    User,
)
from app.schemas.knowledge import DEMO_USER_ID, KnowledgeProposal, SourceType
from app.schemas.listening import (
    EvidenceCategory,
    EvidenceCluster,
    EvidenceObject,
    ListeningSourceSummary,
    ListeningStatus,
    NormalizedListeningSource,
)
from app.services.review_repository import ReviewRepository


class ListeningRepository:
    """Store resumable listening state separately from Career Memory."""

    def persist_ingestion(
        self,
        session: Session,
        source: NormalizedListeningSource,
        evidence: list[EvidenceObject],
        clusters: list[EvidenceCluster],
    ) -> ListeningSourceSummary:
        with session.begin():
            self._ensure_user(session, source.user_id)
            record = session.scalar(
                select(ListeningSource).where(
                    ListeningSource.user_id == source.user_id,
                    ListeningSource.source_type == source.source_type.value,
                    ListeningSource.content_hash == source.content_hash,
                )
            )
            if record is None:
                record = ListeningSource(
                    id=source.id,
                    user_id=source.user_id,
                    source_type=source.source_type.value,
                    label=source.label,
                    original_filename=source.metadata.get("original_filename"),
                    media_type=source.metadata.get("media_type"),
                    raw_text=source.raw_text,
                    source_metadata=source.metadata,
                    provenance=source.provenance,
                    content_hash=source.content_hash,
                    adapter_version=source.adapter_version,
                    status=ListeningStatus.LISTENING.value,
                    received_at=source.received_at,
                )
                session.add(record)
                session.flush()

            existing_by_hash = dict(
                session.execute(
                    select(
                        ListeningEvidence.excerpt_hash,
                        ListeningEvidence.id,
                    ).where(ListeningEvidence.source_id == record.id)
                ).all()
            )
            new_evidence, evidence_ids = self._prepare_evidence(
                source.user_id,
                record.id,
                evidence,
                existing_by_hash,
            )
            session.add_all(new_evidence)
            session.flush()
            self._persist_clusters(
                session,
                source.user_id,
                clusters,
                evidence_ids=evidence_ids,
            )
            record.status = ListeningStatus.READY.value
            session.flush()
            count = session.scalar(
                select(func.count(ListeningEvidence.id)).where(
                    ListeningEvidence.source_id == record.id
                )
            )
        return self._source_summary(record, int(count or 0))

    def list_sources(
        self, session: Session, user_id: uuid.UUID = DEMO_USER_ID
    ) -> list[ListeningSourceSummary]:
        records = session.scalars(
            select(ListeningSource)
            .where(ListeningSource.user_id == user_id)
            .order_by(ListeningSource.received_at.desc())
        ).all()
        counts = dict(
            session.execute(
                select(ListeningEvidence.source_id, func.count(ListeningEvidence.id))
                .where(ListeningEvidence.user_id == user_id)
                .group_by(ListeningEvidence.source_id)
            ).all()
        )
        return [
            self._source_summary(record, counts.get(record.id, 0)) for record in records
        ]

    def list_evidence(
        self,
        session: Session,
        user_id: uuid.UUID = DEMO_USER_ID,
        source_ids: list[uuid.UUID] | None = None,
    ) -> list[EvidenceObject]:
        statement = select(ListeningEvidence).where(
            ListeningEvidence.user_id == user_id
        )
        if source_ids:
            statement = statement.where(ListeningEvidence.source_id.in_(source_ids))
        records = session.scalars(
            statement.order_by(ListeningEvidence.created_at)
        ).all()
        return [self._evidence_object(record) for record in records]

    def persist_clusters(
        self,
        session: Session,
        user_id: uuid.UUID,
        clusters: list[EvidenceCluster],
    ) -> None:
        self._persist_clusters(session, user_id, clusters)
        session.commit()

    def persist_proposal_links(
        self,
        session: Session,
        user_id: uuid.UUID,
        proposals: list[KnowledgeProposal],
        clusters: list[EvidenceCluster],
    ) -> None:
        ReviewRepository().upsert_proposals(session, proposals, user_id)
        cluster_by_evidence = {
            item.id: cluster.id for cluster in clusters for item in cluster.evidence
        }
        for proposal in proposals:
            for reference in proposal.evidence:
                if reference.evidence_id is None:
                    continue
                cluster_id = cluster_by_evidence.get(reference.evidence_id)
                if cluster_id is None:
                    continue
                existing = session.scalar(
                    select(ListeningProposalEvidenceLink.id).where(
                        ListeningProposalEvidenceLink.proposal_id == proposal.id,
                        ListeningProposalEvidenceLink.evidence_id
                        == reference.evidence_id,
                    )
                )
                if existing is None:
                    session.add(
                        ListeningProposalEvidenceLink(
                            user_id=user_id,
                            proposal_id=proposal.id,
                            cluster_id=cluster_id,
                            evidence_id=reference.evidence_id,
                        )
                    )
        session.commit()

    def _persist_clusters(
        self,
        session: Session,
        user_id: uuid.UUID,
        clusters: list[EvidenceCluster],
        *,
        evidence_ids: dict[uuid.UUID, uuid.UUID] | None = None,
    ) -> None:
        canonical_evidence_ids = evidence_ids or {}
        for cluster in clusters:
            record = session.scalar(
                select(ListeningEvidenceCluster).where(
                    ListeningEvidenceCluster.user_id == user_id,
                    ListeningEvidenceCluster.category == cluster.category.value,
                    ListeningEvidenceCluster.normalized_key == cluster.normalized_key,
                )
            )
            conflicts = [
                claim.model_dump(mode="json") for claim in cluster.conflicting_claims
            ]
            if record is None:
                record = ListeningEvidenceCluster(
                    id=cluster.id,
                    user_id=user_id,
                    category=cluster.category.value,
                    label=cluster.label,
                    normalized_key=cluster.normalized_key,
                    has_conflicts=cluster.has_conflicts,
                    conflicting_claims=conflicts,
                )
                session.add(record)
                session.flush()
            else:
                cluster.id = record.id
                record.label = cluster.label
                record.has_conflicts = cluster.has_conflicts
                record.conflicting_claims = conflicts

            conflicting_ids = {
                canonical_evidence_ids.get(evidence_id, evidence_id)
                for claim in cluster.conflicting_claims
                for evidence_id in claim.evidence_ids
            }
            seen_excerpt: set[str] = set()
            seen_evidence_ids: set[uuid.UUID] = set()
            for item in cluster.evidence:
                evidence_id = canonical_evidence_ids.get(item.id, item.id)
                if evidence_id in seen_evidence_ids:
                    continue
                seen_evidence_ids.add(evidence_id)
                existing_member = session.scalar(
                    select(ListeningClusterMember.id).where(
                        ListeningClusterMember.cluster_id == record.id,
                        ListeningClusterMember.evidence_id == evidence_id,
                    )
                )
                if existing_member is not None:
                    continue
                normalized = item.normalized_excerpt or item.raw_excerpt.casefold()
                relationship = "SUPPORTING"
                if evidence_id in conflicting_ids:
                    relationship = "CONFLICTING"
                elif normalized in seen_excerpt:
                    relationship = "DUPLICATE"
                session.add(
                    ListeningClusterMember(
                        user_id=user_id,
                        cluster_id=record.id,
                        evidence_id=evidence_id,
                        relationship_type=relationship,
                    )
                )
                seen_excerpt.add(normalized)

    @classmethod
    def _prepare_evidence(
        cls,
        user_id: uuid.UUID,
        source_id: uuid.UUID,
        evidence: list[EvidenceObject],
        existing_by_hash: dict[str, uuid.UUID],
    ) -> tuple[list[ListeningEvidence], dict[uuid.UUID, uuid.UUID]]:
        """Map repeated excerpts to one durable evidence row and canonical ID."""

        canonical_by_hash = dict(existing_by_hash)
        evidence_ids: dict[uuid.UUID, uuid.UUID] = {}
        records: list[ListeningEvidence] = []
        for item in evidence:
            excerpt_hash = cls._evidence_hash(item)
            evidence_id = canonical_by_hash.get(excerpt_hash)
            if evidence_id is None:
                evidence_id = item.id
                canonical_by_hash[excerpt_hash] = evidence_id
                records.append(
                    cls._evidence_record(
                        user_id,
                        source_id,
                        item,
                        excerpt_hash=excerpt_hash,
                    )
                )
            evidence_ids[item.id] = evidence_id
        return records, evidence_ids

    @staticmethod
    def _evidence_hash(item: EvidenceObject) -> str:
        excerpt_value = item.normalized_excerpt or item.raw_excerpt
        return hashlib.sha256(
            f"{item.category.value}:{excerpt_value}".encode()
        ).hexdigest()

    @staticmethod
    def _evidence_record(
        user_id: uuid.UUID,
        source_id: uuid.UUID,
        item: EvidenceObject,
        *,
        excerpt_hash: str,
    ) -> ListeningEvidence:
        return ListeningEvidence(
            id=item.id,
            user_id=user_id,
            source_id=source_id,
            source_type=item.source_type.value,
            raw_excerpt=item.raw_excerpt,
            normalized_excerpt=item.normalized_excerpt,
            excerpt_hash=excerpt_hash,
            category=item.category.value,
            confidence=Decimal(str(item.confidence)),
            location=item.location,
            provenance=item.provenance,
            extracted_at=item.extracted_at,
        )

    @staticmethod
    def _evidence_object(record: ListeningEvidence) -> EvidenceObject:
        return EvidenceObject(
            id=record.id,
            source_id=record.source_id,
            source_type=SourceType(record.source_type),
            raw_excerpt=record.raw_excerpt,
            normalized_excerpt=record.normalized_excerpt,
            category=EvidenceCategory(record.category),
            confidence=float(record.confidence),
            location=record.location,
            provenance=record.provenance,
            extracted_at=record.extracted_at,
        )

    @staticmethod
    def _source_summary(
        record: ListeningSource, evidence_count: int
    ) -> ListeningSourceSummary:
        return ListeningSourceSummary(
            id=record.id,
            source_type=SourceType(record.source_type),
            label=record.label,
            original_filename=record.original_filename,
            media_type=record.media_type,
            content_hash=record.content_hash,
            status=ListeningStatus(record.status),
            metadata=record.source_metadata,
            received_at=record.received_at,
            created_at=record.created_at,
            evidence_count=evidence_count,
        )

    @staticmethod
    def _ensure_user(session: Session, user_id: uuid.UUID) -> None:
        if session.get(User, user_id) is None:
            session.add(
                User(
                    id=user_id,
                    clerk_user_id=f"listening-demo-{user_id}",
                    email=f"listening-demo-{user_id}@example.invalid",
                    display_name="Sprint 5 Demo User",
                )
            )
            session.flush()
