# LLM AI Scheduler

A local-only demo service that suggests appointment slots using a deterministic scheduler and LLM-powered parsing/explanations.

## Features

- **POST /suggest** — Accepts either:
  - `availability_text`: Free text describing patient + provider availability (parsed by LLM)
  - `structured_availability`: Pre-normalized JSON
- **LLM integration** (OpenAI-compatible):
  - Converts free text to strict JSON schema
  - Generates 1–2 sentence explanations per suggested slot
  - Robust JSON extraction with Pydantic validation and retry on failure
- **Deterministic scheduler**:
  - Time zones (zoneinfo)
  - Slot length (default 30m), buffer between appointments (default 10m)
  - Excludes conflicts, respects business hours and preferred days/times

## Requirements

- Python 3.11+
- OpenAI API key (or compatible endpoint)

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# or: .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Environment variables
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"   # optional, for custom endpoints
export OPENAI_MODEL="gpt-4o-mini"                    # optional, default model
```

## Run

```bash
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or with Makefile
make run
```

Then open **http://localhost:8000** in your browser for the web UI.

## Test

```bash
pytest tests/ -v

# Or with Makefile
make test
```

## API Examples

### 1. Free-text availability

```bash
curl -X POST http://localhost:8000/suggest \
  -H "Content-Type: application/json" \
  -d @data/sample_requests/text_availability.json
```

### 2. Structured JSON availability

```bash
curl -X POST http://localhost:8000/suggest \
  -H "Content-Type: application/json" \
  -d @data/sample_requests/structured_availability.json
```

## Project Structure

```
llm-ai-scheduler/
├── app/
│   ├── __init__.py
│   ├── main.py       # FastAPI app, POST /suggest
│   ├── llm.py        # LLMClient (OpenAI-compatible)
│   ├── schema.py     # Pydantic models
│   └── scheduler.py  # Deterministic slot computation
├── tests/
│   ├── test_scheduler.py   # Scheduler unit tests
│   └── test_llm_parsing.py # Mocked LLM parsing tests
├── data/
│   └── sample_requests/
│       ├── text_availability.json
│       └── structured_availability.json
├── requirements.txt
├── Makefile
└── README.md
```

## License

MIT
