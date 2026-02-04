"""Simple RAG: retrieve relevant chunks and generate answers."""

from pathlib import Path

from app.llm import LLMClient

DOCS_DIR = Path(__file__).parent.parent / "data" / "documents"
PATIENT_DOCS_DIR = Path(__file__).parent.parent / "data" / "patient_docs"


def _load_documents(doc_dir: Path) -> list[tuple[str, str]]:
    """Load all .md, .txt, and .pdf files from docs dir. Returns list of (filename, content)."""
    chunks = []
    if not doc_dir.exists():
        return chunks
    for path in doc_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        chunks.append((path.name, text))
    for path in doc_dir.glob("*.txt"):
        text = path.read_text(encoding="utf-8")
        chunks.append((path.name, text))
    # For PDFs, we'd need a PDF reader library, but for now we'll skip
    # for path in doc_dir.glob("*.pdf"):
    #     # text = extract_text_from_pdf(path)
    #     pass
    return chunks


def _load_scheduler_documents() -> list[tuple[str, str]]:
    """Load scheduler FAQ documents."""
    return _load_documents(DOCS_DIR)


def _load_patient_documents() -> list[tuple[str, str]]:
    """Load uploaded patient documents."""
    return _load_documents(PATIENT_DOCS_DIR)


def _split_into_chunks(text: str, chunk_size: int = 400) -> list[str]:
    """Split text into overlapping chunks by paragraph, then by size."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = []
    current_len = 0
    for p in paragraphs:
        if current_len + len(p) > chunk_size and current:
            chunks.append("\n\n".join(current))
            current = [p]
            current_len = len(p)
        else:
            current.append(p)
            current_len += len(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _score_chunk(chunk: str, query: str) -> float:
    """Simple keyword overlap score (case-insensitive)."""
    q_words = set(w.lower() for w in query.split() if len(w) > 2)
    c_words = set(w.lower() for w in chunk.split())
    if not q_words:
        return 0.0
    return len(q_words & c_words) / len(q_words)


def retrieve(query: str, top_k: int = 3, doc_type: str = "scheduler") -> list[tuple[str, str]]:
    """
    Retrieve top-k relevant chunks from documents.
    Returns list of (source_file, chunk_text).
    doc_type: "scheduler" or "patient"
    """
    if doc_type == "patient":
        docs = _load_patient_documents()
    else:
        docs = _load_scheduler_documents()
    
    all_chunks: list[tuple[str, str, float]] = []
    for filename, content in docs:
        for chunk in _split_into_chunks(content):
            score = _score_chunk(chunk, query)
            if score > 0:
                all_chunks.append((filename, chunk, score))
    all_chunks.sort(key=lambda x: x[2], reverse=True)
    return [(f, c) for f, c, _ in all_chunks[:top_k]]


def ask(query: str, top_k: int = 3, doc_type: str = "scheduler") -> tuple[str, list[str]]:
    """
    RAG: retrieve relevant chunks, then generate answer.
    Returns (answer, list of source filenames).
    doc_type: "scheduler" or "patient"
    """
    chunks_with_sources = retrieve(query, top_k=top_k, doc_type=doc_type)
    if not chunks_with_sources:
        doc_name = "patient documents" if doc_type == "patient" else "scheduler documentation"
        return (
            f"I couldn't find relevant information in the {doc_name}. Try rephrasing your question or upload more documents.",
            [],
        )

    context = "\n\n---\n\n".join(
        f"[From {f}]\n{c}" for f, c in chunks_with_sources
    )
    sources = list(dict.fromkeys(f for f, _ in chunks_with_sources))

    llm = LLMClient()
    prompt = f"""Use ONLY the following context to answer the question. If the answer is not in the context, say so. Be concise.

Context:
{context}

Question: {query}

Answer:"""

    answer = llm._chat([{"role": "user", "content": prompt}])
    return answer.strip(), sources
