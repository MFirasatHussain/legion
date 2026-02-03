"""Deterministic scheduler for computing valid appointment slots."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.schema import ExistingAppointment, StructuredAvailability, TimeRange


def _parse_time(s: str) -> tuple[int, int]:
    """Parse HH:MM to (hour, minute)."""
    parts = s.split(":")
    return int(parts[0]), int(parts[1])


def _time_in_range(
    dt: datetime,
    tz: ZoneInfo,
    time_range: TimeRange,
) -> bool:
    """Check if datetime falls within a time range (HH:MM) in given timezone."""
    local = dt.astimezone(tz).time()
    sh, sm = _parse_time(time_range.start)
    eh, em = _parse_time(time_range.end)
    start_min = sh * 60 + sm
    end_min = eh * 60 + em
    curr_min = local.hour * 60 + local.minute
    return start_min <= curr_min < end_min


def _datetime_in_preferred_times(
    dt: datetime,
    tz: ZoneInfo,
    preferred_times: list[TimeRange],
) -> bool:
    """Check if datetime falls within any preferred time window."""
    if not preferred_times:
        return True
    return any(_time_in_range(dt, tz, tr) for tr in preferred_times)


def _day_in_preferred_days(dt: datetime, tz: ZoneInfo, preferred_days: list[int]) -> bool:
    """Check if datetime's weekday is in preferred_days (0=Monday, 6=Sunday)."""
    local = dt.astimezone(tz)
    # Python: Monday=0, Sunday=6
    weekday = local.weekday()
    return weekday in preferred_days


def _conflicts_with_existing(
    slot_start: datetime,
    slot_end: datetime,
    existing: list[ExistingAppointment],
    tz: ZoneInfo,
) -> bool:
    """Check if slot overlaps with any existing appointment."""
    for appt in existing:
        try:
            appt_start = datetime.fromisoformat(appt.start.replace("Z", "+00:00"))
            appt_end = datetime.fromisoformat(appt.end.replace("Z", "+00:00"))
        except ValueError:
            continue
        # Normalize to same timezone for comparison
        if appt_start.tzinfo is None:
            appt_start = appt_start.replace(tzinfo=tz)
        if appt_end.tzinfo is None:
            appt_end = appt_end.replace(tzinfo=tz)
        slot_start_tz = slot_start if slot_start.tzinfo else slot_start.replace(tzinfo=tz)
        slot_end_tz = slot_end if slot_end.tzinfo else slot_end.replace(tzinfo=tz)
        # Overlap: slot starts before appt ends AND slot ends after appt starts
        if slot_start_tz < appt_end and slot_end_tz > appt_start:
            return True
    return False


def _respects_buffer(
    slot_start: datetime,
    slot_end: datetime,
    existing: list[ExistingAppointment],
    buffer_minutes: int,
    tz: ZoneInfo,
) -> bool:
    """Check that slot has buffer_minutes gap from existing appointments."""
    if buffer_minutes <= 0:
        return True
    for appt in existing:
        try:
            appt_start = datetime.fromisoformat(appt.start.replace("Z", "+00:00"))
            appt_end = datetime.fromisoformat(appt.end.replace("Z", "+00:00"))
        except ValueError:
            continue
        if appt_start.tzinfo is None:
            appt_start = appt_start.replace(tzinfo=tz)
        if appt_end.tzinfo is None:
            appt_end = appt_end.replace(tzinfo=tz)
        slot_start_tz = slot_start if slot_start.tzinfo else slot_start.replace(tzinfo=tz)
        slot_end_tz = slot_end if slot_end.tzinfo else slot_end.replace(tzinfo=tz)
        # Slot must end at least buffer_minutes before next appt
        if slot_end_tz <= appt_start:
            gap = (appt_start - slot_end_tz).total_seconds() / 60
            if gap < buffer_minutes:
                return False
        # Slot must start at least buffer_minutes after previous appt
        elif slot_start_tz >= appt_end:
            gap = (slot_start_tz - appt_end).total_seconds() / 60
            if gap < buffer_minutes:
                return False
    return True


def compute_slots(
    availability: StructuredAvailability,
    max_slots: int = 5,
) -> list[dict[str, str]]:
    """
    Compute valid appointment slots from normalized availability.
    Returns list of dicts with start_iso, end_iso, provider_id.
    """
    tz = ZoneInfo(availability.timezone)
    slot_mins = availability.slot_length_minutes
    buffer_mins = availability.buffer_minutes
    bh = availability.business_hours
    dr = availability.date_range
    existing = availability.existing_appointments
    preferred_days = availability.preferred_days
    preferred_times = availability.preferred_times or []

    # Parse date range
    start_date = date.fromisoformat(dr.start)
    end_date = date.fromisoformat(dr.end)

    slots: list[dict[str, str]] = []
    current = start_date

    while current <= end_date and len(slots) < max_slots:
        # Build day start/end in timezone
        sh, sm = _parse_time(bh.start)
        eh, em = _parse_time(bh.end)
        day_start = datetime(
            current.year, current.month, current.day, sh, sm, 0, tzinfo=tz
        )
        day_end = datetime(
            current.year, current.month, current.day, eh, em, 0, tzinfo=tz
        )

        # Iterate in slot-sized steps
        slot_start = day_start
        while slot_start < day_end and len(slots) < max_slots:
            slot_end = slot_start + timedelta(minutes=slot_mins)

            if slot_end > day_end:
                break

            # Check preferred day
            if not _day_in_preferred_days(slot_start, tz, preferred_days):
                slot_start = slot_end
                continue

            # Check preferred times
            if not _datetime_in_preferred_times(slot_start, tz, preferred_times):
                slot_start = slot_end
                continue

            # Check conflicts
            if _conflicts_with_existing(slot_start, slot_end, existing, tz):
                slot_start = slot_end
                continue

            # Check buffer
            if not _respects_buffer(
                slot_start, slot_end, existing, buffer_mins, tz
            ):
                slot_start = slot_end
                continue

            slots.append({
                "start_iso": slot_start.isoformat(),
                "end_iso": slot_end.isoformat(),
                "provider_id": availability.provider_id,
            })
            slot_start = slot_end

        current += timedelta(days=1)

    return slots[:max_slots]
