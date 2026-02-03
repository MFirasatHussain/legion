"""Pydantic models for request/response and normalized availability schema."""

from typing import Optional

from pydantic import BaseModel, Field, model_validator


# --- Normalized availability schema (used by scheduler) ---


class TimeRange(BaseModel):
    """Time range in HH:MM format."""

    start: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Start time HH:MM")
    end: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="End time HH:MM")


class DateRange(BaseModel):
    """Date range in ISO format."""

    start: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date YYYY-MM-DD")
    end: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date YYYY-MM-DD")


class ExistingAppointment(BaseModel):
    """Existing appointment slot (conflict)."""

    start: str  # ISO 8601 datetime
    end: str  # ISO 8601 datetime


class StructuredAvailability(BaseModel):
    """Normalized availability schema for deterministic scheduling."""

    provider_id: str = Field(..., description="Provider identifier")
    timezone: str = Field(..., description="IANA timezone e.g. America/New_York")
    slot_length_minutes: int = Field(default=30, ge=5, le=120)
    buffer_minutes: int = Field(default=10, ge=0, le=60)
    business_hours: TimeRange = Field(
        default_factory=lambda: TimeRange(start="09:00", end="17:00")
    )
    date_range: DateRange = Field(..., description="Search window for slots")
    existing_appointments: list[ExistingAppointment] = Field(default_factory=list)
    preferred_days: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4],
        description="Weekday numbers 0=Monday, 6=Sunday",
    )
    preferred_times: list[TimeRange] = Field(
        default_factory=list,
        description="Preferred time windows within business hours",
    )


# --- Request / Response ---


class SuggestRequest(BaseModel):
    """Request body for POST /suggest."""

    availability_text: Optional[str] = Field(
        default=None,
        description="Free text describing patient + provider availability",
    )
    structured_availability: Optional[StructuredAvailability] = Field(
        default=None,
        description="Pre-normalized availability JSON",
    )

    @model_validator(mode="after")
    def require_one_source(self) -> "SuggestRequest":
        if not self.availability_text and not self.structured_availability:
            raise ValueError("Either availability_text or structured_availability is required")
        return self


class SuggestedSlot(BaseModel):
    """A single suggested appointment slot."""

    start_iso: str = Field(..., description="ISO 8601 start datetime")
    end_iso: str = Field(..., description="ISO 8601 end datetime")
    provider_id: str = Field(..., description="Provider identifier")
    explanation: str = Field(..., description="LLM-generated explanation (1-2 sentences)")


class SuggestResponse(BaseModel):
    """Response from POST /suggest."""

    slots: list[SuggestedSlot] = Field(..., description="Top 5 suggested slots")
    raw_availability_used: Optional[StructuredAvailability] = Field(
        default=None,
        description="The normalized availability used (for debugging)",
    )
