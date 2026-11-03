"""Semantic Search Service.

Performs intelligent semantic book searching using Sentence Transformers embeddings
and FAISS vector similarity, discovering relevant books even when exact keywords
do not match.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore
from services.google_books_service import GoogleBooksService

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """Semantic search engine leveraging embeddings and FAISS index."""

    @classmethod
    def index_books(cls, books: List[Dict[str, Any]]) -> List[int]:
        """Indexes candidate books into the FAISS vector database with embeddings."""
        if not books:
            return []

        vector_store = VectorStore()
        unindexed_books = []

        for b in books:
            volume_id = b.get("id") or b.get("googleBookId", "")
            if volume_id and not vector_store.has_book(volume_id):
                unindexed_books.append(b)

        if not unindexed_books:
            return []

        # Batch compute embeddings for unindexed books
        rep_texts = [EmbeddingService.build_book_representation(b) for b in unindexed_books]
        embeddings = EmbeddingService.get_embeddings_batch(rep_texts)

        # Store in FAISS
        indices = vector_store.add_books(unindexed_books, embeddings)
        return indices

    @classmethod
    def search(
        cls,
        query: str,
        candidate_books: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Performs semantic similarity search for a query.
        
        Args:
            query: User's natural-language query.
            candidate_books: Optional pre-retrieved candidate pool from Google Books API.
            top_k: Maximum number of ranked results to return.

        Returns:
            List of book dictionaries with 'semantic_similarity' score (0.0 to 1.0).
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        vector_store = VectorStore()

        # If candidate books are provided, ensure they are indexed first
        candidate_ids = []
        if candidate_books:
            cls.index_books(candidate_books)
            candidate_ids = [
                b.get("id") or b.get("googleBookId", "")
                for b in candidate_books
                if (b.get("id") or b.get("googleBookId"))
            ]
        elif vector_store.total_books() == 0:
            # Seed vector store with initial relevant books from Google Books API
            api_res = GoogleBooksService.search_books(clean_query, max_results=30)
            fetched = api_res.get("books", [])
            cls.index_books(fetched)
            candidate_ids = [b["id"] for b in fetched if "id" in b]

        # Generate query embedding
        query_embedding = EmbeddingService.get_embedding(clean_query)

        # Search FAISS vector database
        filter_ids = candidate_ids if candidate_ids else None
        matches = vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_volume_ids=filter_ids,
        )

        ranked_books = []
        for book, sim in matches:
            b_copy = dict(book)
            b_copy["semantic_similarity"] = float(round(sim, 4))
            b_copy["semantic_similarity_percent"] = int(round(sim * 100))
            ranked_books.append(b_copy)

        return ranked_books

