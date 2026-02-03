"""Tests for LLM parsing with mocked client."""

from unittest.mock import MagicMock, patch

import pytest

from app.llm import LLMClient
from app.schema import DateRange, StructuredAvailability


@pytest.fixture
def valid_json_response():
    """Valid JSON string that parses to StructuredAvailability."""
    return """
```json
{
  "provider_id": "dr-test",
  "timezone": "America/New_York",
  "slot_length_minutes": 30,
  "buffer_minutes": 10,
  "business_hours": {"start": "09:00", "end": "17:00"},
  "date_range": {"start": "2025-02-03", "end": "2025-02-10"},
  "existing_appointments": [
    {"start": "2025-02-03T10:00:00-05:00", "end": "2025-02-03T10:30:00-05:00"}
  ],
  "preferred_days": [0, 1, 2, 3, 4],
  "preferred_times": [{"start": "09:00", "end": "12:00"}]
}
```
"""


@pytest.fixture
def raw_json_response():
    """Raw JSON without markdown."""
    return '{"provider_id":"dr-raw","timezone":"Europe/London","slot_length_minutes":45,"buffer_minutes":5,"business_hours":{"start":"08:00","end":"18:00"},"date_range":{"start":"2025-03-01","end":"2025-03-07"},"existing_appointments":[],"preferred_days":[1,2,3],"preferred_times":[]}'


def test_extract_json_from_markdown():
    """LLMClient extracts JSON from markdown code block."""
    text = 'Some text\n```json\n{"foo": "bar"}\n```\nmore'
    result = LLMClient._extract_json(text)
    assert '{"foo": "bar"}' in result or '"foo"' in result


def test_extract_json_raw_brace():
    """LLMClient extracts JSON from raw { } in text."""
    text = 'Here is the result: {"a": 1}'
    result = LLMClient._extract_json(text)
    assert "{" in result and "}" in result


@patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
def test_parse_availability_text_success(valid_json_response):
    """parse_availability_text returns StructuredAvailability when LLM returns valid JSON."""
    client = LLMClient()
    client._chat = MagicMock(return_value=valid_json_response)

    result = client.parse_availability_text("Doctor available Mon-Fri 9-5")

    assert isinstance(result, StructuredAvailability)
    assert result.provider_id == "dr-test"
    assert result.timezone == "America/New_York"
    assert result.slot_length_minutes == 30
    assert result.date_range.start == "2025-02-03"
    assert result.date_range.end == "2025-02-10"
    assert len(result.existing_appointments) == 1


@patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
def test_parse_availability_text_raw_json(raw_json_response):
    """parse_availability_text handles raw JSON without markdown."""
    client = LLMClient()
    client._chat = MagicMock(return_value=raw_json_response)

    result = client.parse_availability_text("Availability in London")

    assert isinstance(result, StructuredAvailability)
    assert result.provider_id == "dr-raw"
    assert result.timezone == "Europe/London"
    assert result.slot_length_minutes == 45


@patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
def test_parse_availability_text_retry_on_invalid():
    """parse_availability_text retries with repair prompt when first response is invalid."""
    client = LLMClient()
    # First call returns invalid JSON, second returns valid
    valid_retry = '{"provider_id":"fixed","timezone":"UTC","slot_length_minutes":30,"buffer_minutes":10,"business_hours":{"start":"09:00","end":"17:00"},"date_range":{"start":"2025-02-01","end":"2025-02-05"},"existing_appointments":[],"preferred_days":[0,1,2,3,4],"preferred_times":[]}'
    client._chat = MagicMock(side_effect=["{ invalid json", valid_retry])

    result = client.parse_availability_text("Some text")

    assert isinstance(result, StructuredAvailability)
    assert result.provider_id == "fixed"
    assert client._chat.call_count == 2


@patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
def test_explain_slots_returns_list():
    """explain_slots returns one explanation per slot."""
    client = LLMClient()
    client._chat = MagicMock(
        return_value='["First slot is early morning.", "Second slot is after lunch."]'
    )

    slots = [
        {"start_iso": "2025-02-03T09:00:00", "end_iso": "2025-02-03T09:30:00", "provider_id": "dr-x"},
        {"start_iso": "2025-02-03T14:00:00", "end_iso": "2025-02-03T14:30:00", "provider_id": "dr-x"},
    ]
    av = StructuredAvailability(
        provider_id="dr-x",
        timezone="America/New_York",
        date_range=DateRange(start="2025-02-03", end="2025-02-10"),
    )

    explanations = client.explain_slots(slots, av)

    assert len(explanations) == 2
    assert "First slot" in explanations[0] or "early" in explanations[0].lower()
    assert "Second slot" in explanations[1] or "lunch" in explanations[1].lower()
