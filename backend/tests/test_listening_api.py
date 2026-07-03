"""API tests for source ingestion, evidence retrieval, and proposal handoff."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.knowledge import get_reasoning_pipeline
from app.api.listening import get_listening_repository
from app.main import app
from app.schemas.listening import ListeningSourceSummary, ListeningStatus
from app.services.llm import LocalSemanticReasoningProvider
from app.services.pipeline import KnowledgeReasoningPipeline


class InMemoryListeningRepository:
    """API-test repository that exercises routes without a PostgreSQL service."""

    def __init__(self) -> None:
        self.sources: list[ListeningSourceSummary] = []
        self.evidence = []
        self.proposal_links: list[tuple[str, uuid.UUID]] = []

    def persist_ingestion(self, session, source, evidence, clusters):
        del session, clusters
        summary = ListeningSourceSummary(
            id=source.id,
            source_type=source.source_type,
            label=source.label,
            original_filename=source.metadata.get("original_filename"),
            media_type=source.metadata.get("media_type"),
            content_hash=source.content_hash,
            status=ListeningStatus.READY,
            metadata=source.metadata,
            received_at=source.received_at,
            created_at=datetime.now(UTC),
            evidence_count=len(evidence),
        )
        self.sources = [item for item in self.sources if item.id != source.id]
        self.sources.append(summary)
        self.evidence = [item for item in self.evidence if item.source_id != source.id]
        self.evidence.extend(evidence)
        return summary

    def list_sources(self, session):
        del session
        return self.sources

    def list_evidence(self, session, user_id=None, source_ids=None):
        del session, user_id
        if source_ids:
            return [item for item in self.evidence if item.source_id in source_ids]
        return self.evidence

    def persist_clusters(self, session, user_id, clusters):
        del session, user_id, clusters

    def persist_proposal_links(self, session, user_id, proposals, clusters):
        del session, user_id, clusters
        self.proposal_links.extend(
            (proposal.id, reference.evidence_id)
            for proposal in proposals
            for reference in proposal.evidence
            if reference.evidence_id
        )


@pytest.fixture
def listening_client():
    repository = InMemoryListeningRepository()
    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_listening_repository] = lambda: repository
    app.dependency_overrides[get_reasoning_pipeline] = lambda: (
        KnowledgeReasoningPipeline(LocalSemanticReasoningProvider())
    )
    with TestClient(app) as client:
        yield client, repository
    app.dependency_overrides = original


def test_submit_list_and_read_evidence(listening_client) -> None:
    client, _ = listening_client
    submitted = client.post(
        "/api/listening/sources",
        json={
            "source_type": "RESUME",
            "label": "July resume",
            "raw_text": "Skills\nPython, SQL",
            "original_filename": "resume.txt",
        },
    )

    assert submitted.status_code == 200
    body = submitted.json()
    assert body["source"]["status"] == "READY"
    assert body["source"]["label"] == "July resume"
    assert body["evidence"]
    source_id = body["source"]["id"]

    sources = client.get("/api/listening/sources")
    evidence = client.get(f"/api/listening/evidence?source_id={source_id}")
    clusters = client.get(f"/api/listening/clusters?source_id={source_id}")

    assert sources.status_code == evidence.status_code == clusters.status_code == 200
    assert sources.json()[0]["original_filename"] == "resume.txt"
    assert all(item["source_id"] == source_id for item in evidence.json())
    assert clusters.json()[0]["evidence"]


def test_generate_listening_proposals_preserves_approval_boundary(
    listening_client,
) -> None:
    client, repository = listening_client
    source_id = client.post(
        "/api/listening/sources",
        json={
            "source_type": "MANUAL",
            "label": "Manual skills",
            "raw_text": "Skills: Python",
        },
    ).json()["source"]["id"]

    response = client.post("/api/listening/proposals", json={"source_ids": [source_id]})

    assert response.status_code == 200
    body = response.json()
    assert body["proposals"]
    assert all(
        proposal["approval_state"] == "NEEDS_REVIEW" for proposal in body["proposals"]
    )
    assert all(proposal["evidence"] for proposal in body["proposals"])
    assert repository.proposal_links
