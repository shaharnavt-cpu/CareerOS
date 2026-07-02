"""API tests for proposal generation and the approval boundary."""

from fastapi.testclient import TestClient

from app.api.knowledge import get_reasoning_pipeline
from app.main import app
from app.services.llm import LocalSemanticReasoningProvider
from app.services.pipeline import KnowledgeReasoningPipeline

app.dependency_overrides[get_reasoning_pipeline] = lambda: KnowledgeReasoningPipeline(
    LocalSemanticReasoningProvider()
)
client = TestClient(app)


def test_create_proposals_runs_the_reasoning_pipeline() -> None:
    response = client.post(
        "/api/knowledge/proposals",
        json={
            "raw_source": "Skills\nPython, SQL",
            "source_type": "RESUME",
            "source_name": "resume.txt",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["provider"] == "local-semantic-v1"
    assert len(body["proposals"]) == 2
    assert all(proposal["evidence"] for proposal in body["proposals"])


def test_rejecting_a_proposal_never_requires_a_database_write() -> None:
    generated = client.post(
        "/api/knowledge/proposals",
        json={"raw_source": "Skills\nPython", "source_type": "RESUME"},
    ).json()["proposals"][0]

    response = client.post(
        "/api/knowledge/proposals/review",
        json={"proposal": generated, "decision": "REJECT"},
    )

    assert response.status_code == 200
    assert response.json()["proposal"]["approval_state"] == "REJECTED"
    assert response.json()["canonical_entity_id"] is None
