"""Pytest configuration and fixtures."""

import pytest

from app.schema import (
    DateRange,
    ExistingAppointment,
    StructuredAvailability,
    TimeRange,
)


@pytest.fixture
def sample_availability() -> StructuredAvailability:
    """Minimal valid availability for testing."""
    return StructuredAvailability(
        provider_id="dr-smith",
        timezone="America/New_York",
        slot_length_minutes=30,
        buffer_minutes=10,
        business_hours=TimeRange(start="09:00", end="17:00"),
        date_range=DateRange(start="2025-02-03", end="2025-02-07"),
        existing_appointments=[],
        preferred_days=[0, 1, 2, 3, 4],
        preferred_times=[],
    )


@pytest.fixture
def availability_with_conflicts() -> StructuredAvailability:
    """Availability with existing appointments to exclude."""
    return StructuredAvailability(
        provider_id="dr-jones",
        timezone="America/Los_Angeles",
        slot_length_minutes=30,
        buffer_minutes=10,
        business_hours=TimeRange(start="09:00", end="17:00"),
        date_range=DateRange(start="2025-02-03", end="2025-02-05"),
        existing_appointments=[
            ExistingAppointment(
                start="2025-02-03T10:00:00-08:00",
                end="2025-02-03T10:30:00-08:00",
            ),
            ExistingAppointment(
                start="2025-02-03T11:00:00-08:00",
                end="2025-02-03T11:30:00-08:00",
            ),
        ],
        preferred_days=[0, 1, 2, 3, 4],
        preferred_times=[],
    )


@pytest.fixture
def availability_with_preferred_times() -> StructuredAvailability:
    """Availability with preferred time windows."""
    return StructuredAvailability(
        provider_id="dr-wong",
        timezone="UTC",
        slot_length_minutes=30,
        buffer_minutes=5,
        business_hours=TimeRange(start="08:00", end="18:00"),
        date_range=DateRange(start="2025-02-03", end="2025-02-04"),
        existing_appointments=[],
        preferred_days=[0],
        preferred_times=[
            TimeRange(start="09:00", end="12:00"),
            TimeRange(start="14:00", end="16:00"),
        ],
    )
