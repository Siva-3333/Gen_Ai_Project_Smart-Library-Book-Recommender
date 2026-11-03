"""Optional Open-Source LLM Service (Ollama Integration).

Connects to a local Ollama instance (e.g. Llama-3, Mistral, Phi-3) for grounded
recommendation explanations and conversational book discovery.
If Ollama is unavailable or unconfigured, seamlessly falls back to Python-based
deterministic grounded explanations so the platform never fails.
"""

import os
import time
import logging
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
CONNECT_TIMEOUT = 1.2
GENERATE_TIMEOUT = 8.0


class LLMService:
    """Service for interacting with local Ollama or falling back to rule-based generation."""

    _last_check_time: float = 0.0
    _is_available: bool = False
    _check_interval: float = 30.0  # seconds between live Ollama heartbeats

    @classmethod
    def is_available(cls) -> bool:
        """Checks if local Ollama daemon is currently running and reachable."""
        now = time.time()
        if now - cls._last_check_time < cls._check_interval:
            return cls._is_available

        cls._last_check_time = now
        url = f"{DEFAULT_OLLAMA_URL}/api/tags"
        try:
            resp = requests.get(url, timeout=CONNECT_TIMEOUT)
            if resp.status_code == 200:
                cls._is_available = True
                logger.info("Local Ollama service detected at %s (Model: %s)", DEFAULT_OLLAMA_URL, DEFAULT_OLLAMA_MODEL)
                return True
        except Exception:
            pass

        cls._is_available = False
        return False

    @classmethod
    def generate_grounded_explanation(
        cls,
        book: Dict[str, Any],
        query: str,
        query_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generates an honest, grounded explanation for why a book matches the query."""
        if cls.is_available():
            try:
                title = book.get("title", "Unknown Title")
                authors = book.get("authors_str", "Unknown Author")
                category = book.get("category", "General")
                desc = book.get("description", "")
                if not desc or desc == "Not available":
                    desc = f"Subject overview in {category}."
                else:
                    desc = desc[:450]

                prompt = (
                    "You are an academic book discovery assistant. Explain why this book is recommended for the user query.\n"
                    "RULES:\n"
                    "1. Use ONLY the real information below. Never invent details.\n"
                    "2. Exactly 1 to 2 clear, professional sentences.\n\n"
                    f"User Query: {query}\n"
                    f"Book Title: {title}\n"
                    f"Authors: {authors}\n"
                    f"Category: {category}\n"
                    f"Description: {desc}\n\n"
                    "Recommendation Explanation:"
                )

                payload = {
                    "model": DEFAULT_OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 75},
                }

                res = requests.post(
                    f"{DEFAULT_OLLAMA_URL}/api/generate",
                    json=payload,
                    timeout=GENERATE_TIMEOUT,
                )
                if res.status_code == 200:
                    text = res.json().get("response", "").strip()
                    if text:
                        return text
            except Exception as e:
                logger.debug("Ollama generation timed out or failed (%s), using rule-based explanation.", e)

        # Resilient Python Grounded Explanation
        return cls._rule_based_explanation(book, query, query_analysis)

    @classmethod
    def _rule_based_explanation(
        cls,
        book: Dict[str, Any],
        query: str,
        query_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Deterministic Python explanation grounded strictly on Google Books metadata."""
        subject = (query_analysis.get("subject") if query_analysis else "") or query
        category = book.get("category", "")
        level = query_analysis.get("reading_level", "All Levels") if query_analysis else "All Levels"
        rating = book.get("rating")
        sim_pct = book.get("semantic_similarity_percent") or book.get("recommendation_score", 80)

        reasons = []
        if sim_pct >= 85:
            reasons.append(f"provides a strong {sim_pct}% semantic match for your goal in '{subject}'")
        else:
            reasons.append(f"matches your query on '{subject}'")

        if category and category != "General":
            reasons.append(f"covers core topics in {category}")

        if level and level != "All Levels":
            reasons.append(f"is calibrated for {level.lower()} readers")

        if rating and rating >= 4.0:
            reasons.append(f"holds a high community rating of {rating}/5")

        return f"Recommended because this volume {', and '.join(reasons)}."

    @classmethod
    def conversational_reply(
        cls,
        user_message: str,
        retrieved_books: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        query_analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generates a conversational assistant response for the interactive discovery chat."""
        if cls.is_available() and retrieved_books:
            try:
                # Format retrieved books as grounded context
                context_lines = []
                for idx, b in enumerate(retrieved_books[:4], 1):
                    t = b.get("title", "")
                    a = b.get("authors_str", "")
                    c = b.get("category", "")
                    score = b.get("recommendation_score", "")
                    context_lines.append(f"{idx}. '{t}' by {a} (Category: {c}, Relevance: {score}%)")
                books_context = "\n".join(context_lines)

                prompt = (
                    "You are the Smart Library AI Book Discovery Assistant. Answer the user's message warmly and guide them.\n"
                    "Reference the actual retrieved books below.\n"
                    "Do NOT invent books or details not in the list.\n\n"
                    f"User Message: {user_message}\n\n"
                    f"Top Retrieved Books from Google Books Cloud:\n{books_context}\n\n"
                    "Assistant Response (friendly, concise, 2-3 sentences max):"
                )

                payload = {
                    "model": DEFAULT_OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.4, "num_predict": 120},
                }

                res = requests.post(
                    f"{DEFAULT_OLLAMA_URL}/api/generate",
                    json=payload,
                    timeout=GENERATE_TIMEOUT,
                )
                if res.status_code == 200:
                    text = res.json().get("response", "").strip()
                    if text:
                        return text
            except Exception as e:
                logger.debug("Ollama conversational chat failed (%s), using grounded fallback.", e)

        # Grounded Python Fallback Response
        if not retrieved_books:
            return (
                f"I searched Google Books for '{user_message}', but couldn't find close matches. "
                "Could you try broadening your subject or specifying a topic like Python, Artificial Intelligence, or History?"
            )

        top_book = retrieved_books[0]
        top_title = top_book.get("title", "this volume")
        top_cat = top_book.get("category", "your discipline")
        level_str = ""
        if query_analysis and query_analysis.get("reading_level") not in (None, "All Levels"):
            level_str = f" for {query_analysis['reading_level'].lower()} readers"

        return (
            f"I found {len(retrieved_books)} relevant volumes{level_str} in {top_cat}. "
            f"The highest semantic match is '{top_title}', which closely aligns with your objective. "
            "You can explore the breakdown below and click 'Add to My Library' to save any title!"
        )

