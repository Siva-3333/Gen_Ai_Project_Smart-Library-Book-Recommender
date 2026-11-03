"""FAISS Vector Database Service.

Provides efficient similarity search, indexing, duplicate avoidance, and retrieval
for book embeddings using FAISS (IndexFlatIP for cosine similarity) with unique
Google Books volume ID tracking.
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384


class VectorStore:
    """FAISS-backed vector store for book embeddings with unique volume ID deduplication."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorStore, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes FAISS index and metadata lookup tables."""
        self._dim = EMBEDDING_DIM
        self._books_by_id: Dict[str, Dict[str, Any]] = {}
        self._volume_id_to_idx: Dict[str, int] = {}
        self._idx_to_volume_id: Dict[int, str] = {}
        self._embeddings_matrix: Optional[np.ndarray] = None
        self._faiss_index = None
        self._use_faiss = False

        self._init_faiss()

    def _init_faiss(self):
        """Attempts to initialize native FAISS IndexFlatIP (Inner Product for Cosine Similarity)."""
        try:
            import faiss
            self._faiss_index = faiss.IndexFlatIP(self._dim)
            self._use_faiss = True
            logger.info("FAISS IndexFlatIP initialized successfully (dimension=%d).", self._dim)
        except Exception as e:
            logger.warning(
                "FAISS unavailable (%s). Using vectorized Cosine Matrix fallback.",
                e,
            )
            self._use_faiss = False
            self._faiss_index = None

    def has_book(self, volume_id: str) -> bool:
        """Checks if a book volume ID is already present in the index."""
        if not volume_id:
            return False
        return volume_id in self._volume_id_to_idx

    def get_book(self, volume_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached book dictionary by volume ID."""
        return self._books_by_id.get(volume_id)

    def total_books(self) -> int:
        """Returns total unique books stored."""
        return len(self._volume_id_to_idx)

    def add_book(self, book: Dict[str, Any], embedding: np.ndarray) -> int:
        """Adds a single book and embedding, avoiding duplicates.
        
        Returns the index of the book in the store.
        """
        volume_id = book.get("id") or book.get("googleBookId", "")
        if not volume_id:
            logger.debug("Skipping book without unique volume ID")
            return -1

        with self._lock:
            # If already exists, update book metadata and return existing index
            if volume_id in self._volume_id_to_idx:
                self._books_by_id[volume_id].update(book)
                return self._volume_id_to_idx[volume_id]

            # Normalize embedding
            vec = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
            norm = np.linalg.norm(vec)
            if norm > 1e-9:
                vec = vec / norm

            idx = len(self._idx_to_volume_id)
            self._volume_id_to_idx[volume_id] = idx
            self._idx_to_volume_id[idx] = volume_id
            self._books_by_id[volume_id] = dict(book)

            if self._use_faiss and self._faiss_index is not None:
                self._faiss_index.add(vec)
            else:
                if self._embeddings_matrix is None:
                    self._embeddings_matrix = vec
                else:
                    self._embeddings_matrix = np.vstack([self._embeddings_matrix, vec])

            return idx

    def add_books(self, books: List[Dict[str, Any]], embeddings: np.ndarray) -> List[int]:
        """Adds a batch of books and embeddings, filtering duplicates."""
        if not books:
            return []

        indices = []
        new_books = []
        new_vectors = []

        with self._lock:
            for book, vec in zip(books, embeddings):
                volume_id = book.get("id") or book.get("googleBookId", "")
                if not volume_id:
                    continue

                if volume_id in self._volume_id_to_idx:
                    self._books_by_id[volume_id].update(book)
                    indices.append(self._volume_id_to_idx[volume_id])
                    continue

                idx = len(self._idx_to_volume_id) + len(new_books)
                norm_vec = np.asarray(vec, dtype=np.float32)
                norm = np.linalg.norm(norm_vec)
                if norm > 1e-9:
                    norm_vec = norm_vec / norm

                new_books.append((idx, volume_id, dict(book)))
                new_vectors.append(norm_vec)
                indices.append(idx)

            if new_books:
                v_matrix = np.vstack(new_vectors).astype(np.float32)

                for idx, volume_id, b_dict in new_books:
                    self._volume_id_to_idx[volume_id] = idx
                    self._idx_to_volume_id[idx] = volume_id
                    self._books_by_id[volume_id] = b_dict

                if self._use_faiss and self._faiss_index is not None:
                    self._faiss_index.add(v_matrix)
                else:
                    if self._embeddings_matrix is None:
                        self._embeddings_matrix = v_matrix
                    else:
                        self._embeddings_matrix = np.vstack([self._embeddings_matrix, v_matrix])

                logger.info(
                    "Indexed %d new books into FAISS Vector Database (Total: %d).",
                    len(new_books),
                    len(self._idx_to_volume_id),
                )

        return indices

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        filter_volume_ids: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Searches vector index for books closest to query_embedding.
        
        Returns:
            List of (book_dictionary, cosine_similarity_score).
        """
        if self.total_books() == 0:
            return []

        q_vec = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        norm = np.linalg.norm(q_vec)
        if norm > 1e-9:
            q_vec = q_vec / norm

        top_k = min(top_k, self.total_books())
        if top_k <= 0:
            return []

        results: List[Tuple[Dict[str, Any], float]] = []

        with self._lock:
            # If filtering to a candidate subset of volume IDs:
            if filter_volume_ids:
                valid_ids = set(filter_volume_ids)
                candidate_indices = [
                    idx for idx, vid in self._idx_to_volume_id.items() if vid in valid_ids
                ]
                if not candidate_indices:
                    return []

                # Compute cosine similarities manually for the candidate subset
                for idx in candidate_indices:
                    vid = self._idx_to_volume_id[idx]
                    book = self._books_by_id[vid]
                    if self._use_faiss and self._faiss_index is not None:
                        try:
                            # Reconstruct vector from FAISS
                            book_vec = self._faiss_index.reconstruct(idx)
                            sim = float(np.dot(q_vec[0], book_vec))
                        except Exception:
                            sim = 0.5
                    elif self._embeddings_matrix is not None:
                        sim = float(np.dot(q_vec[0], self._embeddings_matrix[idx]))
                    else:
                        sim = 0.5

                    sim = float(np.clip(sim, 0.0, 1.0))
                    results.append((book, sim))

                results.sort(key=lambda x: x[1], reverse=True)
                return results[:top_k]

            # Global FAISS Search
            if self._use_faiss and self._faiss_index is not None:
                try:
                    distances, indices = self._faiss_index.search(q_vec, top_k)
                    for idx, sim in zip(indices[0], distances[0]):
                        if idx < 0 or idx not in self._idx_to_volume_id:
                            continue
                        vid = self._idx_to_volume_id[idx]
                        book = self._books_by_id.get(vid)
                        if book:
                            results.append((book, float(np.clip(sim, 0.0, 1.0))))
                    return results
                except Exception as e:
                    logger.warning("FAISS search failed, using fallback: %s", e)

            # Fallback Matrix Search
            if self._embeddings_matrix is not None:
                sims = np.dot(self._embeddings_matrix, q_vec[0])
                ranked_indices = np.argsort(sims)[::-1][:top_k]
                for idx in ranked_indices:
                    vid = self._idx_to_volume_id.get(int(idx))
                    if vid and vid in self._books_by_id:
                        book = self._books_by_id[vid]
                        results.append((book, float(np.clip(sims[idx], 0.0, 1.0))))

        return results

    def clear(self):
        """Clears all stored books and vectors."""
        with self._lock:
            self._books_by_id.clear()
            self._volume_id_to_idx.clear()
            self._idx_to_volume_id.clear()
            self._embeddings_matrix = None
            self._init_faiss()

