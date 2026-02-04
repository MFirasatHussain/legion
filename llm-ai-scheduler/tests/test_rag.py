"""Tests for RAG module."""

from unittest.mock import MagicMock, patch

import pytest

from app.rag import retrieve, _load_scheduler_documents, _split_into_chunks, ask


def test_load_documents():
    """Documents are loaded from data/documents/."""
    docs = _load_scheduler_documents()
    assert len(docs) >= 1
    names = [n for n, _ in docs]
    assert "scheduler_faq.md" in names


def test_split_into_chunks():
    """Text is split into chunks."""
    text = "Para one.\n\nPara two.\n\nPara three."
    chunks = _split_into_chunks(text, chunk_size=100)
    assert len(chunks) >= 1
    assert "Para one" in chunks[0]


def test_retrieve_returns_relevant_chunks():
    """Retrieve finds chunks matching query keywords."""
    chunks = retrieve("timezone formats", top_k=2)
    assert len(chunks) <= 2
    for filename, chunk in chunks:
        assert "timezone" in chunk.lower() or "time" in chunk.lower()


def test_retrieve_empty_query():
    """Retrieve with no matching keywords returns empty."""
    chunks = retrieve("xyznonexistent123", top_k=3)
    assert len(chunks) == 0


@patch("app.rag.LLMClient")
def test_ask_returns_answer_and_sources(MockLLMClient):
    """ask() returns answer and source filenames."""
    from app.rag import ask

    mock_llm = MagicMock()
    mock_llm._chat.return_value = "Use IANA timezone names like America/New_York."
    MockLLMClient.return_value = mock_llm

    answer, sources = ask("What timezone formats?", top_k=2)
    assert len(answer) > 0
    assert isinstance(sources, list)
    mock_llm._chat.assert_called_once()


@patch("app.rag.LLMClient")
@patch("app.rag._load_patient_documents")
def test_ask_patient_documents(mock_load_docs, MockLLMClient):
    """Ask questions about patient documents."""
    # Mock patient documents with content that will match the query
    mock_load_docs.return_value = [("patient.md", "Patient takes medication Lisinopril for blood pressure.")]
    
    mock_llm = MagicMock()
    mock_llm._chat.return_value = "The patient is taking Lisinopril."
    MockLLMClient.return_value = mock_llm

    answer, sources = ask("medication", top_k=2, doc_type="patient")
    assert len(answer) > 0
    assert isinstance(sources, list)
    mock_llm._chat.assert_called_once()
