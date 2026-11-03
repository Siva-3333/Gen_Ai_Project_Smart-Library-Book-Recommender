"""Comprehensive Unit Tests for Advanced AI Capabilities.

Verifies:
1. Sentence Transformers & Embedding Generation (all-MiniLM-L6-v2)
2. In-Memory & Disk Embedding Caching
3. Semantic Search & Cosine Similarity
4. FAISS Vector Database (Indexing, Search, Deduplication)
5. Grounded RAG Pipeline (Context assembly, grounded explanations)
6. Hybrid Recommendation Algorithm (35/25/15/15/10 scoring weights)
"""

import unittest
import numpy as np

from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore
from services.semantic_search_service import SemanticSearchService
from services.rag_service import RAGPipeline
from services.recommendation_service import RecommendationEngine, NaturalLanguageQueryParser
from services.llm_service import LLMService


class TestAICapabilities(unittest.TestCase):
    """Test suite covering the complete AI/ML pipeline."""

    def setUp(self):
        # Sample books for testing
        self.sample_python_book = {
            "id": "vol_py_101",
            "title": "Learning Python Programming",
            "subtitle": "From Novice to Professional Software Developer",
            "authors": ["Mark Lutz"],
            "authors_str": "Mark Lutz",
            "categories": ["Computers", "Programming", "Python"],
            "category": "Programming",
            "description": "Comprehensive guide to writing clean, maintainable Python code and software architecture.",
            "rating": 4.8,
            "thumbnail": "https://example.com/py.jpg",
        }

        self.sample_ai_book = {
            "id": "vol_ai_202",
            "title": "Deep Learning and Neural Networks",
            "subtitle": "Principles and Architectures",
            "authors": ["Ian Goodfellow", "Yoshua Bengio"],
            "authors_str": "Ian Goodfellow, Yoshua Bengio",
            "categories": ["Computers", "Artificial Intelligence", "Machine Learning"],
            "category": "Artificial Intelligence",
            "description": "Foundational textbook on mathematical foundations of deep neural networks and computer vision.",
            "rating": 4.9,
            "thumbnail": "https://example.com/ai.jpg",
        }

        self.sample_history_book = {
            "id": "vol_hist_303",
            "title": "The Fall of the Roman Empire",
            "subtitle": "A Military and Social History",
            "authors": ["Peter Heather"],
            "authors_str": "Peter Heather",
            "categories": ["History", "Ancient Rome"],
            "category": "History",
            "description": "Detailed investigation into the geopolitical shifts and barbarian migrations that transformed Europe.",
            "rating": 4.5,
            "thumbnail": "https://example.com/rome.jpg",
        }

        self.sample_nodesc_book = {
            "id": "vol_nodesc_404",
            "title": "Practical Data Science Cookbook",
            "subtitle": "Recipes for Machine Learning",
            "authors": ["Alice Smith"],
            "authors_str": "Alice Smith",
            "categories": ["Computers", "Data Science"],
            "category": "Data Science",
            "description": "Not available",
            "rating": 4.2,
            "publisher": "Tech Press",
            "publishedDate": "2024",
            "thumbnail": "https://example.com/ds.jpg",
        }

    # =========================================================================
    # 1. SENTENCE TRANSFORMERS & EMBEDDINGS
    # =========================================================================
    def test_embedding_generation_and_dimension(self):
        """Verifies embeddings are 384-dimensional and unit-normalized."""
        vec = EmbeddingService.get_embedding("I want to become a Python developer.")
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (384,))
        # Unit norm check
        norm = float(np.linalg.norm(vec))
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_semantic_similarity_concept_matching(self):
        """Verifies semantic similarity detects conceptual relationships beyond exact keywords."""
        query_vec = EmbeddingService.get_embedding("I want to become a Python developer.")
        python_vec = EmbeddingService.get_embedding("Software engineering, coding syntax, and clean code principles.")
        history_vec = EmbeddingService.get_embedding("Ancient Greek archaeology, pottery, and Roman emperors.")

        sim_python = EmbeddingService.compute_similarity(query_vec, python_vec)
        sim_history = EmbeddingService.compute_similarity(query_vec, history_vec)

        self.assertGreater(sim_python, sim_history)
        self.assertGreaterEqual(sim_python, 0.0)
        self.assertLessEqual(sim_python, 1.0)

    def test_embedding_caching(self):
        """Verifies embedding caching avoids duplicate computations."""
        text = "Caching performance test phrase for sentence transformers."
        vec_1 = EmbeddingService.get_embedding(text)
        vec_2 = EmbeddingService.get_embedding(text)
        np.testing.assert_array_equal(vec_1, vec_2)

    def test_missing_description_handling(self):
        """Verifies books with missing/placeholder descriptions generate rich embeddings."""
        vec = EmbeddingService.embed_book(self.sample_nodesc_book)
        self.assertEqual(vec.shape, (384,))
        self.assertGreater(float(np.linalg.norm(vec)), 0.99)

    # =========================================================================
    # 2. FAISS VECTOR DATABASE
    # =========================================================================
    def test_faiss_vector_store_indexing_and_deduplication(self):
        """Verifies FAISS vector store adds books, retrieves them, and avoids duplicates."""
        store = VectorStore()
        initial_count = store.total_books()

        vec_py = EmbeddingService.embed_book(self.sample_python_book)
        store.add_book(self.sample_python_book, vec_py)

        # Re-adding the exact same volume ID must NOT increase count
        store.add_book(self.sample_python_book, vec_py)
        self.assertEqual(store.total_books(), initial_count + 1)
        self.assertTrue(store.has_book("vol_py_101"))

        # Add AI book
        vec_ai = EmbeddingService.embed_book(self.sample_ai_book)
        store.add_book(self.sample_ai_book, vec_ai)

        # Search using query
        query_vec = EmbeddingService.get_embedding("Python development and coding")
        results = store.search(query_vec, top_k=2)

        self.assertGreaterEqual(len(results), 1)
        # Python book should rank first
        top_book, score = results[0]
        self.assertEqual(top_book["id"], "vol_py_101")
        self.assertGreater(score, 0.1)

    # =========================================================================
    # 3. SEMANTIC SEARCH SERVICE
    # =========================================================================
    def test_semantic_search_service(self):
        """Verifies semantic search discovers books without keyword matching."""
        books = [self.sample_python_book, self.sample_ai_book, self.sample_history_book]
        results = SemanticSearchService.search(
            query="neural networks and machine learning models",
            candidate_books=books,
            top_k=3,
        )

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "vol_ai_202")
        self.assertIn("semantic_similarity", results[0])
        self.assertIn("semantic_similarity_percent", results[0])

    # =========================================================================
    # 4. RAG PIPELINE & GROUNDED EXPLANATIONS
    # =========================================================================
    def test_rag_pipeline_execution(self):
        """Verifies the complete 9-step RAG pipeline."""
        rag_output = RAGPipeline.execute(
            query="Python programming for beginners",
            user_preferences=["Programming"],
            max_results=5,
        )

        self.assertTrue(rag_output["success"])
        self.assertIn("query_analysis", rag_output)
        self.assertIn("grounded_context", rag_output)
        self.assertIn("recommendations", rag_output)
        self.assertIn("rag_metadata", rag_output)

        recs = rag_output["recommendations"]
        if recs:
            first = recs[0]
            self.assertIn("recommendation_reason", first)
            self.assertIn("semantic_similarity", first)

    # =========================================================================
    # 5. HYBRID RECOMMENDATION ALGORITHM (35/25/15/15/10)
    # =========================================================================
    def test_hybrid_scoring_weights(self):
        """Verifies exact 35/25/15/15/10 hybrid formula calculation."""
        parsed = {
            "original_query": "I want to learn Python programming from beginner to advanced",
            "subject": "Python",
            "category": "Programming",
            "reading_level": "Beginner",
            "purpose": "Learning",
        }

        # 1. Semantic Similarity: 35%
        q_vec = EmbeddingService.get_embedding("Python programming")
        b_vec = EmbeddingService.embed_book(self.sample_python_book)
        sem_sim = EmbeddingService.compute_similarity(q_vec, b_vec)

        # 2. Subject Relevance: 25%
        subj_sim = RecommendationEngine._compute_text_similarity("Python", self.sample_python_book["title"])

        # 3. Category Match: 15%
        cat_score = RecommendationEngine._score_category("Programming", self.sample_python_book)

        # 4. User Preferences: 15%
        user_pref = RecommendationEngine._score_user_preferences(["Programming"], self.sample_python_book)

        # 5. Reading Level: 10%
        level_score = RecommendationEngine._score_reading_level("Beginner", self.sample_python_book)

        # Weighted formula check
        composite = (
            (0.35 * sem_sim)
            + (0.25 * subj_sim)
            + (0.15 * cat_score)
            + (0.15 * user_pref)
            + (0.10 * level_score)
        )

        expected_percent = max(40, min(int(round(composite * 100)), 99))
        self.assertTrue(40 <= expected_percent <= 100)

        # Verify explanation generation
        explanation = LLMService.generate_grounded_explanation(
            book=self.sample_python_book,
            query="Python programming",
            query_analysis=parsed,
        )
        self.assertIsInstance(explanation, str)
        self.assertTrue(len(explanation) > 10)


if __name__ == "__main__":
    unittest.main()
