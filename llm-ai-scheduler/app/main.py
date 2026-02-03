"""FastAPI application for LLM AI Scheduler."""

from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.llm import LLMClient
from app.scheduler import compute_slots
from app.schema import SuggestRequest, SuggestResponse, SuggestedSlot, StructuredAvailability

app = FastAPI(title="LLM AI Scheduler", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    """Serve the scheduler UI."""
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/suggest", response_model=SuggestResponse)
def suggest(request: SuggestRequest) -> SuggestResponse:
    """
    Suggest top 5 appointment slots.
    Accepts either availability_text (free text) or structured_availability (JSON).
    """
    availability: StructuredAvailability

    if request.structured_availability is not None:
        availability = request.structured_availability
    else:
        if not request.availability_text:
            raise HTTPException(
                status_code=422,
                detail="Either availability_text or structured_availability is required",
            )
        try:
            llm = LLMClient()
            availability = llm.parse_availability_text(request.availability_text)
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except httpx.HTTPStatusError as e:
            msg = f"LLM API error ({e.response.status_code}): "
            if e.response.status_code == 401:
                msg += "Invalid or missing API key. Set OPENAI_API_KEY in your environment."
            else:
                msg += str(e)
            raise HTTPException(status_code=502, detail=msg)

    # Deterministic scheduler computes slots
    raw_slots = compute_slots(availability, max_slots=5)

    if not raw_slots:
        return SuggestResponse(
            slots=[],
            raw_availability_used=availability,
        )

    # LLM generates explanations for each slot
    try:
        llm = LLMClient()
        explanations = llm.explain_slots(raw_slots, availability)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except httpx.HTTPStatusError as e:
        msg = f"LLM API error ({e.response.status_code}): "
        if e.response.status_code == 401:
            msg += "Invalid or missing API key. Set OPENAI_API_KEY in your environment."
        else:
            msg += str(e)
        raise HTTPException(status_code=502, detail=msg)

    slots = [
        SuggestedSlot(
            start_iso=s["start_iso"],
            end_iso=s["end_iso"],
            provider_id=s["provider_id"],
            explanation=explanations[i] if i < len(explanations) else "Slot fits availability.",
        )
        for i, s in enumerate(raw_slots)
    ]

    return SuggestResponse(
        slots=slots,
        raw_availability_used=availability,
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
