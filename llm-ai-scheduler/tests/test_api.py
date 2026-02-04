"""Tests for FastAPI /suggest endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@patch("app.main.LLMClient")
def test_suggest_with_structured_availability(MockLLMClient, client):
    """POST /suggest with structured_availability returns slots without calling LLM for parsing."""
    req = {
        "structured_availability": {
            "provider_id": "dr-test",
            "timezone": "America/New_York",
            "slot_length_minutes": 30,
            "buffer_minutes": 10,
            "business_hours": {"start": "09:00", "end": "17:00"},
            "date_range": {"start": "2025-02-03", "end": "2025-02-07"},
            "existing_appointments": [],
            "preferred_days": [0, 1, 2, 3, 4],
            "preferred_times": [],
        }
    }

    mock_llm = MagicMock()
    mock_llm.explain_slots.return_value = [
        "First available slot.",
        "Second slot.",
        "Third slot.",
        "Fourth slot.",
        "Fifth slot.",
    ]
    MockLLMClient.return_value = mock_llm

    resp = client.post("/suggest", json=req)

    assert resp.status_code == 200
    data = resp.json()
    assert "slots" in data
    assert len(data["slots"]) <= 5
    for slot in data["slots"]:
        assert "start_iso" in slot
        assert "end_iso" in slot
        assert slot["provider_id"] == "dr-test"
        assert "explanation" in slot
    # parse_availability_text should NOT be called (we used structured)
    mock_llm.parse_availability_text.assert_not_called()
    mock_llm.explain_slots.assert_called_once()


def test_suggest_requires_either_input(client):
    """POST /suggest without availability_text or structured_availability returns 422."""
    resp = client.post("/suggest", json={})
    assert resp.status_code == 422


def test_health(client):
    """GET /health returns ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@patch("app.main.rag_ask")
def test_ask_endpoint(MockRagAsk, client):
    """POST /ask returns answer and sources."""
    MockRagAsk.return_value = ("Use IANA timezone names.", ["scheduler_faq.md"])
    resp = client.post("/ask", json={"question": "What timezones?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert "IANA" in data["answer"]
