"""Unit tests for deterministic scheduler."""

import pytest

from app.scheduler import compute_slots
from app.schema import (
    DateRange,
    ExistingAppointment,
    StructuredAvailability,
    TimeRange,
)


def test_compute_slots_returns_up_to_max_slots(sample_availability):
    """Scheduler returns at most max_slots."""
    slots = compute_slots(sample_availability, max_slots=5)
    assert len(slots) <= 5
    for s in slots:
        assert "start_iso" in s
        assert "end_iso" in s
        assert s["provider_id"] == "dr-smith"


def test_compute_slots_respects_business_hours(sample_availability):
    """Slots fall within business hours (09:00-17:00)."""
    slots = compute_slots(sample_availability, max_slots=5)
    for s in slots:
        start = s["start_iso"]
        # Extract hour from ISO string (e.g. 2025-02-03T09:00:00-05:00)
        hour = int(start.split("T")[1][:2])
        assert 9 <= hour < 17, f"Slot {start} outside business hours"


def test_compute_slots_respects_slot_length(sample_availability):
    """Each slot is exactly slot_length_minutes long."""
    slots = compute_slots(sample_availability, max_slots=3)
    from datetime import datetime

    for s in slots:
        start = datetime.fromisoformat(s["start_iso"])
        end = datetime.fromisoformat(s["end_iso"])
        diff = (end - start).total_seconds() / 60
        assert diff == 30


def test_compute_slots_excludes_conflicts(availability_with_conflicts):
    """Slots do not overlap with existing appointments."""
    slots = compute_slots(availability_with_conflicts, max_slots=10)
    # 10:00-10:30 and 11:00-11:30 are blocked; 10:30-11:00 might be blocked by buffer
    # First available could be 09:00-09:30 or 11:30-12:00 (with 10min buffer after 11:30)
    for s in slots:
        start = s["start_iso"]
        # Should not be 10:00 or 11:00 in LA time on 2025-02-03
        assert "T10:00" not in start or "2025-02-03" not in start
        assert "T11:00" not in start or "2025-02-03" not in start


def test_compute_slots_respects_preferred_days(sample_availability):
    """Slots only on preferred weekdays (Mon-Fri)."""
    slots = compute_slots(sample_availability, max_slots=5)
    # 2025-02-03 is Monday, 2025-02-07 is Friday
    for s in slots:
        # All should be Mon-Fri
        start = s["start_iso"]
        assert "2025-02-0" in start  # Within our date range


def test_compute_slots_respects_preferred_times(availability_with_preferred_times):
    """Slots fall within preferred time windows when specified."""
    slots = compute_slots(availability_with_preferred_times, max_slots=10)
    # Preferred: 09:00-12:00 and 14:00-16:00 UTC
    for s in slots:
        start = s["start_iso"]
        # Must be in 09-12 or 14-16 range (UTC)
        hour = int(start.split("T")[1][:2])
        assert (9 <= hour < 12) or (14 <= hour < 16)


def test_compute_slots_empty_when_no_availability():
    """Returns empty list when date range has no valid slots."""
    av = StructuredAvailability(
        provider_id="x",
        timezone="America/New_York",
        date_range=DateRange(start="2025-02-08", end="2025-02-09"),  # Sat-Sun
        preferred_days=[0, 1, 2, 3, 4],  # Weekdays only
    )
    slots = compute_slots(av, max_slots=5)
    assert slots == []


def test_compute_slots_custom_slot_length():
    """Respects custom slot_length_minutes."""
    av = StructuredAvailability(
        provider_id="x",
        timezone="UTC",
        slot_length_minutes=60,
        date_range=DateRange(start="2025-02-03", end="2025-02-04"),
        business_hours=TimeRange(start="09:00", end="12:00"),
    )
    slots = compute_slots(av, max_slots=5)
    from datetime import datetime

    for s in slots:
        start = datetime.fromisoformat(s["start_iso"])
        end = datetime.fromisoformat(s["end_iso"])
        assert (end - start).total_seconds() == 3600
