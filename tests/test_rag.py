"""
Tests for the RAG pipeline (rag_engine.py and gemini_client.py).

These tests exercise retrieval logic without requiring a live Gemini API key.
Run with:  python -m pytest tests/ -v
"""

import os
import pytest

from rag_engine import load_knowledge_base, RAGRetriever, _split_into_chunks
from gemini_client import build_prompt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def chunks():
    """Load the knowledge base once for the whole test module."""
    loaded = load_knowledge_base()
    return loaded


@pytest.fixture(scope="module")
def retriever(chunks):
    """Build the TF-IDF retriever once for the whole test module."""
    return RAGRetriever(chunks)


# ---------------------------------------------------------------------------
# Test 1: Knowledge base loading
# ---------------------------------------------------------------------------


def test_knowledge_base_loads_chunks(chunks):
    """The knowledge base must contain at least one chunk."""
    assert len(chunks) > 0, (
        "Knowledge base returned 0 chunks — check that knowledge_base/*.md files exist."
    )


# ---------------------------------------------------------------------------
# Test 2: Chunk structure
# ---------------------------------------------------------------------------


def test_chunks_have_required_fields(chunks):
    """Every chunk must carry 'text', 'source', and 'heading' keys."""
    for chunk in chunks:
        assert "text" in chunk, "Chunk missing 'text' field"
        assert "source" in chunk, "Chunk missing 'source' field"
        assert "heading" in chunk, "Chunk missing 'heading' field"
        assert len(chunk["text"].split()) >= 20, (
            f"Chunk from {chunk['source']} is too short: '{chunk['text'][:60]}'"
        )


# ---------------------------------------------------------------------------
# Test 3: Retrieval returns results for a relevant query
# ---------------------------------------------------------------------------


def test_retriever_returns_results_for_dog_query(retriever):
    """A dog-related query should return at least one chunk."""
    results, confidence = retriever.retrieve("how much should I walk my dog")
    assert len(results) > 0, "Expected at least one result for a dog query"
    assert 0.0 <= confidence <= 1.0, f"Confidence out of range: {confidence}"


# ---------------------------------------------------------------------------
# Test 4: Top-k limit is respected
# ---------------------------------------------------------------------------


def test_retriever_respects_top_k_limit(retriever):
    """retrieve() must never return more than top_k results."""
    for k in (1, 2, 3):
        results, _ = retriever.retrieve("feeding schedule for cats", top_k=k)
        assert len(results) <= k, f"Got {len(results)} results for top_k={k}"


# ---------------------------------------------------------------------------
# Test 5: Confidence is higher for specific queries than nonsense queries
# ---------------------------------------------------------------------------


def test_confidence_is_higher_for_specific_query(retriever):
    """A topic-specific query should score higher than random gibberish."""
    _, specific_conf = retriever.retrieve("dog exercise daily walk requirements")
    _, gibberish_conf = retriever.retrieve("xyzzy blorp flibbertigibbet")
    assert specific_conf >= gibberish_conf, (
        f"Specific query ({specific_conf:.3f}) should outrank gibberish ({gibberish_conf:.3f})"
    )


# ---------------------------------------------------------------------------
# Test 6: Empty query is handled gracefully (no crash)
# ---------------------------------------------------------------------------


def test_empty_query_does_not_crash(retriever):
    """An empty or whitespace-only query must return empty results, not raise."""
    results, confidence = retriever.retrieve("")
    assert results == [], "Empty query should return an empty list"
    assert confidence == 0.0, "Empty query should return confidence 0.0"

    results2, confidence2 = retriever.retrieve("   ")
    assert results2 == []
    assert confidence2 == 0.0


# ---------------------------------------------------------------------------
# Test 7: Species-specific retrieval
# ---------------------------------------------------------------------------


def test_cat_query_retrieves_cat_relevant_content(retriever):
    """A cat-specific query should surface content from cat_care or nutrition."""
    results, _ = retriever.retrieve("what should I feed my cat")
    assert len(results) > 0
    sources = {r["source"] for r in results}
    # At least one result should come from cat- or nutrition-related files
    relevant = {"cat_care", "nutrition"}
    assert sources & relevant, (
        f"Expected a cat or nutrition source, got: {sources}"
    )


# ---------------------------------------------------------------------------
# Test 8: Prompt builder includes retrieved context
# ---------------------------------------------------------------------------


def test_prompt_builder_includes_retrieved_context():
    """build_prompt must embed the chunk text and pet context in the output."""
    chunks = [
        {
            "text": "Dogs need 30 to 60 minutes of exercise daily.",
            "source": "dog_care",
            "heading": "Exercise Requirements",
            "score": 0.45,
        }
    ]
    pet_ctx = "Owner: Ahmed | Pet: Rex (dog)"
    prompt = build_prompt("How much exercise does my dog need?", chunks, pet_context=pet_ctx)

    assert "Dogs need 30 to 60 minutes" in prompt, "Chunk text missing from prompt"
    assert "Rex (dog)" in prompt, "Pet context missing from prompt"
    assert "Dog Care" in prompt, "Source label missing from prompt"


# ---------------------------------------------------------------------------
# Test 9: Prompt builder handles no retrieved chunks gracefully
# ---------------------------------------------------------------------------


def test_prompt_builder_handles_empty_chunks():
    """build_prompt must still produce a valid string when chunks is empty."""
    prompt = build_prompt("Is chocolate safe for dogs?", [], pet_context="")
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "No specific excerpts" in prompt


# ---------------------------------------------------------------------------
# Test 10: Missing API key raises ValueError
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_value_error(monkeypatch):
    """init_gemini() must raise ValueError when GEMINI_API_KEY is absent."""
    # Remove the key from os.environ. Do NOT reload the module — reloading
    # re-runs load_dotenv() which reads .env again and puts the key back,
    # defeating the purpose of monkeypatch.delenv.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    from gemini_client import init_gemini
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        init_gemini()


# ---------------------------------------------------------------------------
# Test 11: Chunk splitter ignores too-short fragments
# ---------------------------------------------------------------------------


def test_chunk_splitter_ignores_short_fragments():
    """Chunks shorter than CHUNK_MIN_WORDS words must be filtered out."""
    minimal_md = "# Title\n\nToo short.\n\n## Real Section\n\n" + ("word " * 25)
    chunks = _split_into_chunks(minimal_md, source="test")
    # "Too short." fragment must not appear
    texts = [c["text"] for c in chunks]
    assert not any("Too short" in t for t in texts), (
        "Short fragment leaked through the minimum-word filter"
    )
