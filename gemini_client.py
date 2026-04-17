"""
Gemini API client for PawPal+ AI Assistant.

Builds RAG-augmented prompts from retrieved knowledge-base chunks and the
user's live pet profile, then calls Google Gemini to generate an answer.
All calls are logged so the system's behaviour is fully auditable.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load .env before anything else so GEMINI_API_KEY is available
load_dotenv()

logger = logging.getLogger("gemini_client")

_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Thresholds for the three-tier confidence label shown in the UI
# ---------------------------------------------------------------------------

_CONF_HIGH = 0.10    # cosine similarity >= this → "high"
_CONF_MEDIUM = 0.05  # cosine similarity >= this → "medium", else "low"

# ---------------------------------------------------------------------------
# System instruction injected at the start of every prompt
# ---------------------------------------------------------------------------

_SYSTEM_INSTRUCTION = (
    "You are PawPal AI, a friendly and knowledgeable pet care assistant built "
    "into the PawPal+ scheduling app. You help pet owners with questions about "
    "their pets' health, nutrition, exercise, grooming, and daily care routines. "
    "You will be given relevant excerpts from a curated pet care knowledge base — "
    "always ground your answer primarily in that context. "
    "If the context does not cover the question, say so honestly and recommend "
    "consulting a veterinarian for health concerns. "
    "Keep answers concise, practical, and warm. Never attempt to diagnose "
    "medical conditions — always direct the owner to a vet for anything clinical."
)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def init_gemini() -> genai.Client:
    """Create and return a Gemini Client instance.

    Reads GEMINI_API_KEY from the environment (loaded from .env by load_dotenv).
    Raises ValueError if the key is missing so the caller can surface a clear
    error message rather than a cryptic API failure.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Create a .env file with GEMINI_API_KEY=<your_key>."
        )

    client = genai.Client(api_key=api_key)
    logger.info("Gemini client initialised (model: %s)", _MODEL)
    return client


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def build_prompt(
    question: str,
    retrieved_chunks: List[dict],
    pet_context: str = "",
) -> str:
    """Compose the full prompt sent to Gemini.

    Structure:
        1. Pet owner context  — who they are and what pets they have
        2. Knowledge base excerpts  — retrieved chunks with source labels
        3. The user's actual question
    """
    # --- Pet context block ---
    if pet_context.strip():
        context_block = f"PET OWNER CONTEXT:\n{pet_context}"
    else:
        context_block = "PET OWNER CONTEXT:\nNo pet profile set yet."

    # --- Retrieved knowledge block ---
    if retrieved_chunks:
        excerpt_lines: List[str] = []
        for i, chunk in enumerate(retrieved_chunks, start=1):
            source_label = chunk["source"].replace("_", " ").title()
            excerpt_lines.append(
                f"[Excerpt {i} — {source_label}: {chunk['heading']}]\n{chunk['text']}"
            )
        knowledge_block = "KNOWLEDGE BASE EXCERPTS:\n" + "\n\n".join(excerpt_lines)
    else:
        knowledge_block = (
            "KNOWLEDGE BASE EXCERPTS:\n"
            "No specific excerpts found. Answer from general knowledge and recommend "
            "a vet if the topic involves health or medication."
        )

    return (
        f"{context_block}\n\n"
        f"{knowledge_block}\n\n"
        f"USER QUESTION:\n{question}\n\n"
        "Please answer the question based on the excerpts above. "
        "Be specific, practical, and reference the pet's name when the owner has provided one."
    )


# ---------------------------------------------------------------------------
# Main query function
# ---------------------------------------------------------------------------


def ask_gemini(
    model: genai.Client,
    question: str,
    retrieved_chunks: List[dict],
    pet_context: str = "",
    confidence: float = 0.0,
    chat_history: Optional[List[dict]] = None,
) -> dict:
    """Send a RAG-augmented question to Gemini and return a structured response.

    Args:
        model:            Initialised Client from init_gemini().
        question:         The user's raw question string.
        retrieved_chunks: Chunks from RAGRetriever.retrieve().
        pet_context:      Plain-text description of the owner's pet setup.
        confidence:       Cosine similarity score from retrieval (0–1).
        chat_history:     Unused for now; reserved for multi-turn support.

    Returns:
        dict with keys:
            answer            — Gemini's text response
            confidence        — raw float score (0–1)
            confidence_label  — "high" | "medium" | "low" | "error"
            sources           — list of unique source names used as context
    """
    try:
        prompt = build_prompt(question, retrieved_chunks, pet_context)

        logger.info(
            "Gemini request | confidence=%.3f | chunks=%d | question='%s...'",
            confidence,
            len(retrieved_chunks),
            question[:60],
        )
        logger.info("=== PROMPT SENT TO GEMINI ===\n%s\n=== END PROMPT ===", prompt)

        response = model.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
            ),
        )
        answer = response.text
        logger.info("=== RESPONSE FROM GEMINI ===\n%s\n=== END RESPONSE ===", answer)

        # Derive the human-readable confidence label
        if confidence >= _CONF_HIGH:
            confidence_label = "high"
        elif confidence >= _CONF_MEDIUM:
            confidence_label = "medium"
        else:
            confidence_label = "low"

        sources = sorted(
            {c["source"].replace("_", " ").title() for c in retrieved_chunks}
        )

        logger.info(
            "Gemini response received | label=%s | sources=%s",
            confidence_label,
            sources,
        )

        return {
            "answer": answer,
            "confidence": confidence,
            "confidence_label": confidence_label,
            "sources": sources,
        }

    except Exception as exc:  # noqa: BLE001 — surface all API errors gracefully
        logger.error("Gemini API error: %s", exc)
        return {
            "answer": (
                "I ran into an error while generating a response. "
                "Please try again or check your API key. "
                f"(Detail: {str(exc)[:120]})"
            ),
            "confidence": 0.0,
            "confidence_label": "error",
            "sources": [],
        }
