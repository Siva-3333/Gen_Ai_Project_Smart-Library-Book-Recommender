"""Sentence Transformer Embedding Service.

Provides dense vector embeddings (384-dim) using the pretrained 'all-MiniLM-L6-v2'
model with in-memory and persistent disk caching for maximum performance.
Handles missing metadata and provides safe fallbacks.
"""

import os
import re
import pickle
import hashlib
import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

# Default model identifier
MODEL_NAME = "all-MiniLM-L6-v2"
LOCAL_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "all-MiniLM-L6-v2")
EMBEDDING_DIM = 384
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "embeddings_cache.pkl")


class EmbeddingService:
    """Singleton service for generating and caching sentence embeddings."""

    _instance = None
    _model = None
    _model_failed = False
    _cache: Dict[str, np.ndarray] = {}
    _cache_dirty = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance

    def _init_service(self):
        """Initializes the embedding cache and prepares model loader."""
        self._load_cache_from_disk()

    @classmethod
    def _load_cache_from_disk(cls):
        """Loads cached embeddings from disk file if available."""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "rb") as f:
                    cls._cache = pickle.load(f)
                logger.info("Loaded %d cached embeddings from %s", len(cls._cache), CACHE_FILE)
            except Exception as e:
                logger.warning("Could not read embedding cache: %s", e)
                cls._cache = {}
        else:
            cls._cache = {}

    @classmethod
    def save_cache_to_disk(cls):
        """Saves current cache to disk file."""
        if not cls._cache:
            return
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(CACHE_FILE, "wb") as f:
                pickle.dump(cls._cache, f)
            cls._cache_dirty = False
            logger.debug("Saved %d embeddings to cache file", len(cls._cache))
        except Exception as e:
            logger.warning("Failed to save embedding cache: %s", e)

    @classmethod
    def _get_model(cls):
        """Lazy-loads the SentenceTransformer model."""
        if cls._model is not None:
            return cls._model

        if cls._model_failed:
            return None

        try:
            from sentence_transformers import SentenceTransformer
            model_file = os.path.join(LOCAL_MODEL_DIR, "model.safetensors")
            is_local_complete = os.path.isdir(LOCAL_MODEL_DIR) and os.path.exists(model_file) and os.path.getsize(model_file) > 85000000
            target = LOCAL_MODEL_DIR if is_local_complete else MODEL_NAME
            logger.info("Loading SentenceTransformer model from '%s'...", target)
            cls._model = SentenceTransformer(target)
            logger.info("SentenceTransformer model loaded successfully.")
            return cls._model
        except Exception as exc:
            logger.warning(
                "Could not load SentenceTransformer ('%s'). Using vectorized fallback: %s",
                MODEL_NAME,
                exc,
            )
            cls._model_failed = True
            return None

    @classmethod
    def _normalize(cls, vec: np.ndarray) -> np.ndarray:
        """Normalizes vector to unit L2 norm for cosine similarity."""
        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            return vec / norm
        return vec

    @classmethod
    def _fallback_embedding(cls, text: str) -> np.ndarray:
        """Generates a deterministic 384-dimensional pseudo-dense semantic vector.
        
        Used as a resilient fallback if PyTorch/Transformers model is still downloading
        or initializing, ensuring zero runtime crashes.
        """
        words = re.findall(r"\w+", text.lower())
        vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        if not words:
            return vec

        for word in words:
            # Deterministic word hashing into 384 dimensions
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % EMBEDDING_DIM
            sign = 1.0 if (h >> 9) & 1 else -1.0
            weight = 1.0 + (len(word) / 10.0)
            vec[idx] += sign * weight

        return cls._normalize(vec)

    @classmethod
    def _make_cache_key(cls, text: str) -> str:
        """Generates a stable cache key for arbitrary text."""
        clean = " ".join(text.strip().lower().split())
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    @classmethod
    def get_embedding(cls, text: str) -> np.ndarray:
        """Encodes a single text string into a 384-dimensional normalized vector."""
        if not text or not text.strip():
            return np.zeros(EMBEDDING_DIM, dtype=np.float32)

        cache_key = cls._make_cache_key(text)
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        model = cls._get_model()
        if model is not None:
            try:
                raw_vec = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
                vec = cls._normalize(np.asarray(raw_vec, dtype=np.float32))
            except Exception as e:
                logger.warning("Encoding failed via model, falling back: %s", e)
                vec = cls._fallback_embedding(text)
        else:
            vec = cls._fallback_embedding(text)

        cls._cache[cache_key] = vec
        cls._cache_dirty = True
        return vec

    @classmethod
    def get_embeddings_batch(cls, texts: List[str]) -> np.ndarray:
        """Encodes a list of texts into a 2D matrix of shape (N, 384)."""
        if not texts:
            return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)

        results = []
        uncached_indices = []
        uncached_texts = []

        for i, t in enumerate(texts):
            key = cls._make_cache_key(t)
            if key in cls._cache:
                results.append((i, cls._cache[key]))
            else:
                uncached_indices.append(i)
                uncached_texts.append(t)

        if uncached_texts:
            model = cls._get_model()
            if model is not None:
                try:
                    batch_vecs = model.encode(
                        uncached_texts,
                        convert_to_numpy=True,
                        show_progress_bar=False,
                    )
                    for idx, raw_v, txt in zip(uncached_indices, batch_vecs, uncached_texts):
                        norm_v = cls._normalize(np.asarray(raw_v, dtype=np.float32))
                        key = cls._make_cache_key(txt)
                        cls._cache[key] = norm_v
                        results.append((idx, norm_v))
                except Exception as e:
                    logger.warning("Batch encoding failed, using fallback: %s", e)
                    for idx, txt in zip(uncached_indices, uncached_texts):
                        v = cls._fallback_embedding(txt)
                        key = cls._make_cache_key(txt)
                        cls._cache[key] = v
                        results.append((idx, v))
            else:
                for idx, txt in zip(uncached_indices, uncached_texts):
                    v = cls._fallback_embedding(txt)
                    key = cls._make_cache_key(txt)
                    cls._cache[key] = v
                    results.append((idx, v))

        cls.save_cache_to_disk()
        # Sort results back to original text order
        results.sort(key=lambda x: x[0])
        return np.vstack([r[1] for r in results]).astype(np.float32)

    @classmethod
    def build_book_representation(cls, book: Dict[str, Any]) -> str:
        """Builds a rich semantic textual representation from book metadata."""
        title = (book.get("title") or "").strip()
        subtitle = (book.get("subtitle") or "").strip()
        category = (book.get("category") or "").strip()
        authors = (book.get("authors_str") or "").strip()
        desc = (book.get("description") or "").strip()

        # Handle missing or placeholder descriptions gracefully
        if not desc or desc in ("Not available", "None", ""):
            publisher = (book.get("publisher") or "").strip()
            date = (book.get("publishedDate") or "").strip()
            parts = [title]
            if subtitle:
                parts.append(subtitle)
            if category and category != "General":
                parts.append(f"Discipline: {category}")
            if authors:
                parts.append(f"Authors: {authors}")
            if publisher:
                parts.append(f"Publisher: {publisher}")
            if date:
                parts.append(f"Published: {date}")
            parts.append(f"Subject reference on {category or title}")
            return ". ".join(p for p in parts if p) + "."

        # Truncate overly long descriptions (keep first 800 characters for high semantic signal)
        cleaned_desc = re.sub(r"<[^>]+>", " ", desc)
        cleaned_desc = " ".join(cleaned_desc.split())[:800]

        parts = [title]
        if subtitle:
            parts.append(subtitle)
        if category and category != "General":
            parts.append(f"Category: {category}")
        if authors:
            parts.append(f"By {authors}")
        parts.append(cleaned_desc)
        return ". ".join(p for p in parts if p) + "."

    @classmethod
    def embed_book(cls, book: Dict[str, Any]) -> np.ndarray:
        """Computes and caches the embedding vector for a book dictionary."""
        book_id = book.get("id") or book.get("googleBookId", "")
        rep_text = cls.build_book_representation(book)
        cache_key = f"book:{book_id}:{cls._make_cache_key(rep_text)}" if book_id else cls._make_cache_key(rep_text)

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        vec = cls.get_embedding(rep_text)
        cls._cache[cache_key] = vec
        cls._cache_dirty = True
        return vec

    @classmethod
    def compute_similarity(cls, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Computes cosine similarity between two normalized vectors (range 0.0 to 1.0)."""
        if vec_a is None or vec_b is None:
            return 0.0
        dot = float(np.dot(vec_a, vec_b))
        # Ensure within [0.0, 1.0]
        return float(np.clip(dot, 0.0, 1.0))
