"""FastAPI application for LLM AI Scheduler."""

from pathlib import Path

import httpx
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.llm import LLMClient
from app.rag import ask as rag_ask
from app.scheduler import compute_slots
from app.schema import SuggestRequest, SuggestResponse, SuggestedSlot, StructuredAvailability

app = FastAPI(title="LLM AI Scheduler", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"
PATIENT_DOCS_DIR = Path(__file__).parent.parent / "data" / "patient_docs"
PATIENT_DOCS_DIR.mkdir(exist_ok=True)

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


@app.post("/ask")
def ask_question(body: dict = Body(...)) -> dict:
    """
    RAG: Ask a question about the scheduler. Answers are generated from docs in data/documents/.
    Body: {"question": "your question"}
    """
    q = body.get("question", "").strip()
    if not q:
        raise HTTPException(status_code=422, detail="question is required")
    try:
        answer, sources = rag_ask(q, doc_type="scheduler")
        return {"answer": answer, "sources": sources}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except httpx.HTTPStatusError as e:
        msg = f"LLM API error ({e.response.status_code}): "
        if e.response.status_code == 401:
            msg += "Invalid or missing API key. Set OPENAI_API_KEY in your environment."
        else:
            msg += str(e)
        raise HTTPException(status_code=502, detail=msg)


@app.post("/upload")
def upload_file(file: UploadFile = File(...)) -> dict:
    """
    Upload a patient document for RAG queries.
    Supports .txt and .md files.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    allowed_extensions = {".txt", ".md"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save file
    file_path = PATIENT_DOCS_DIR / file.filename
    try:
        with open(file_path, "wb") as f:
            content = file.file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    return {"message": f"File '{file.filename}' uploaded successfully", "filename": file.filename}


@app.post("/ask_patient")
def ask_patient_question(body: dict = Body(...)) -> dict:
    """
    RAG: Ask a question about patient documents. Answers are generated from uploaded patient docs.
    Body: {"question": "your question"}
    """
    q = body.get("question", "").strip()
    if not q:
        raise HTTPException(status_code=422, detail="question is required")
    try:
        answer, sources = rag_ask(q, doc_type="patient")
        return {"answer": answer, "sources": sources}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except httpx.HTTPStatusError as e:
        msg = f"LLM API error ({e.response.status_code}): "
        if e.response.status_code == 401:
            msg += "Invalid or missing API key. Set OPENAI_API_KEY in your environment."
        else:
            msg += str(e)
        raise HTTPException(status_code=502, detail=msg)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
