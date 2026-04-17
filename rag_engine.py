"""
RAG Engine for PawPal+ AI Assistant.

Loads markdown knowledge base files, splits them into chunks, and retrieves
the most relevant chunks for a user query using TF-IDF cosine similarity.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Logging — writes to file + stdout so every retrieval action is recorded
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("pawpal_rag.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("rag_engine")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE_DIR = Path(__file__).parent / "knowledge_base"
CHUNK_MIN_WORDS = 20  # Discard very short fragments that won't help retrieval


# ---------------------------------------------------------------------------
# Knowledge base loading and chunking
# ---------------------------------------------------------------------------


def load_knowledge_base(kb_dir: Path = KNOWLEDGE_BASE_DIR) -> List[dict]:
    """Read all .md files in kb_dir and return a flat list of text chunks.

    Each chunk is a dict with keys:
        text    — cleaned plain text of the chunk
        source  — stem of the originating file (e.g. "dog_care")
        heading — nearest markdown heading, for display/citation purposes
    """
    chunks: List[dict] = []

    if not kb_dir.exists():
        logger.warning("Knowledge base directory not found: %s", kb_dir)
        return chunks

    md_files = sorted(kb_dir.glob("*.md"))
    if not md_files:
        logger.warning("No .md files found in knowledge base directory: %s", kb_dir)
        return chunks

    for md_file in md_files:
        logger.info("Loading: %s", md_file.name)
        text = md_file.read_text(encoding="utf-8")
        file_chunks = _split_into_chunks(text, source=md_file.stem)
        chunks.extend(file_chunks)
        logger.info("  -> %d chunks from %s", len(file_chunks), md_file.name)

    logger.info("Knowledge base loaded: %d total chunks", len(chunks))
    return chunks


def _split_into_chunks(text: str, source: str) -> List[dict]:
    """Split a markdown document into sections by heading, then clean the text."""
    chunks: List[dict] = []

    # Split on any markdown heading (# / ## / ###)
    raw_sections = re.split(r"\n(?=#{1,3} )", text)

    for section in raw_sections:
        section = section.strip()
        if not section:
            continue

        # Capture the heading label for metadata
        heading_match = re.match(r"^#{1,3}\s+(.+)", section)
        heading = heading_match.group(1).strip() if heading_match else "General"

        # Strip markdown syntax for cleaner retrieval text
        clean = re.sub(r"#{1,3}\s+", "", section)          # remove heading markers
        clean = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)    # bold
        clean = re.sub(r"\*(.+?)\*", r"\1", clean)         # italic
        clean = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", clean)  # links
        clean = re.sub(r"`(.+?)`", r"\1", clean)            # inline code
        clean = re.sub(r"\|[^\n]+\|", " ", clean)           # markdown table rows
        clean = re.sub(r"-{3,}", " ", clean)                # horizontal rules
        clean = re.sub(r"\s+", " ", clean).strip()

        if len(clean.split()) < CHUNK_MIN_WORDS:
            continue  # too short to be useful

        chunks.append({"text": clean, "source": source, "heading": heading})

    return chunks


# ---------------------------------------------------------------------------
# TF-IDF Retriever
# ---------------------------------------------------------------------------


class RAGRetriever:
    """Retrieves the most relevant knowledge-base chunks for a natural-language query.

    Uses TF-IDF vectorisation and cosine similarity — no heavy ML models or
    external APIs required, keeping the system self-contained and fast.
    """

    def __init__(self, chunks: List[dict]) -> None:
        self.chunks = chunks
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=8000,
            ngram_range=(1, 2),  # unigrams + bigrams improve topic matching
        )

        if chunks:
            corpus = [c["text"] for c in chunks]
            self._tfidf_matrix = self._vectorizer.fit_transform(corpus)
            logger.info("RAGRetriever ready — %d chunks indexed", len(chunks))
        else:
            self._tfidf_matrix = None
            logger.warning("RAGRetriever initialised with empty knowledge base")

    def retrieve(self, query: str, top_k: int = 3) -> Tuple[List[dict], float]:
        """Return the top_k most relevant chunks and a confidence score.

        Args:
            query:  The user's natural-language question.
            top_k:  Maximum number of chunks to return.

        Returns:
            A tuple of (results, confidence) where:
                results    — list of chunk dicts, each augmented with a "score" key
                confidence — float in [0, 1]; the highest cosine similarity found
        """
        if self._tfidf_matrix is None or not self.chunks:
            logger.warning("Retrieval attempted on empty knowledge base")
            return [], 0.0

        if not query or not query.strip():
            logger.warning("Empty query received; returning empty results")
            return [], 0.0

        query_vec = self._vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Sort by similarity descending and take top_k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results: List[dict] = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.0:
                results.append({**self.chunks[idx], "score": score})

        confidence = float(similarities[top_indices[0]]) if len(results) > 0 else 0.0

        logger.info(
            "Query: '%s...' | chunks returned: %d | confidence: %.3f",
            query[:50],
            len(results),
            confidence,
        )
        return results, confidence
