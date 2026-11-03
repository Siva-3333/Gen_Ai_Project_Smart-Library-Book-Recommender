"""Unit tests for the Intelligent Recommendation Engine and NLP Parser."""

import unittest
from services.recommendation_service import (
    NaturalLanguageQueryParser,
    RecommendationEngine,
)


class TestRecommendationEngine(unittest.TestCase):
    """Test suite verifying the Python recommendation engine and NLP parsing."""

    def test_nlp_parser_beginner_to_advanced_python(self):
        query = "I want to learn Python programming from beginner to advanced."
        parsed = NaturalLanguageQueryParser.parse(query)

        self.assertEqual(parsed["category"], "Programming")
        self.assertIn("Python", parsed["subject"])
        self.assertEqual(parsed["reading_level"], "Beginner to Advanced")
        self.assertIn("Learning", parsed["purpose"])

    def test_nlp_parser_ai_machine_learning(self):
        query = "Recommend books about Artificial Intelligence and Deep Learning"
        parsed = NaturalLanguageQueryParser.parse(query)

        self.assertEqual(parsed["category"], "Artificial Intelligence")
        self.assertIn("Artificial Intelligence", parsed["subject"])

    def test_nlp_parser_quantity_and_author(self):
        query = "Top 5 history books by Yuval Noah Harari"
        parsed = NaturalLanguageQueryParser.parse(query)

        self.assertEqual(parsed["requested_count"], 5)
        self.assertEqual(parsed["category"], "History")
        self.assertEqual(parsed["preferred_author"], "Yuval Noah Harari")

    def test_tfidf_cosine_similarity(self):
        sim_high = RecommendationEngine._compute_text_similarity(
            "Python data science and machine learning",
            "Python Data Science Handbook: Essential Tools for Working with Data",
        )
        sim_low = RecommendationEngine._compute_text_similarity(
            "Python data science and machine learning",
            "Medieval French Poetry and Ancient Literature",
        )

        self.assertGreater(sim_high, sim_low)
        self.assertGreaterEqual(sim_high, 0.0)
        self.assertLessEqual(sim_high, 1.0)

    def test_scoring_weights_composite(self):
        sample_book = {
            "id": "book_ml_1",
            "title": "Machine Learning with Python",
            "subtitle": "A Practical Guide for Beginners",
            "categories": ["Computers", "Machine Learning"],
            "description": "An introduction to machine learning algorithms in Python.",
            "rating": 4.6,
        }

        parsed = {
            "subject": "Machine Learning",
            "category": "Machine Learning",
            "reading_level": "Beginner",
            "purpose": "Learning",
        }

        # Subject similarity (35%)
        subj_sim = RecommendationEngine._compute_text_similarity("Machine Learning", sample_book["title"])
        # Category score (25%)
        cat_score = RecommendationEngine._score_category("Machine Learning", sample_book)
        # User pref score (20%)
        user_pref = RecommendationEngine._score_user_preferences(["Machine Learning", "Programming"], sample_book)
        # Reading level score (10%)
        lvl_score = RecommendationEngine._score_reading_level("Beginner", sample_book)
        # Description relevance (10%)
        desc_sim = RecommendationEngine._compute_text_similarity("Machine Learning", sample_book["description"])

        composite = (
            (0.35 * subj_sim)
            + (0.25 * cat_score)
            + (0.20 * user_pref)
            + (0.10 * lvl_score)
            + (0.10 * desc_sim)
        )

        final_score = int(round(composite * 100))
        self.assertTrue(50 <= final_score <= 100)

        # Verify explanation text
        explanation = RecommendationEngine._generate_explanation(sample_book, parsed, final_score)
        self.assertIn("Recommended because", explanation)
        self.assertIn("Machine Learning", explanation)


if __name__ == "__main__":
    unittest.main()

