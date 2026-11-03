"""Hybrid AI Recommendation Engine.

Combines:
- Semantic similarity (Sentence Transformers + FAISS): 35%
- Subject relevance (n-gram / keyword overlap): 25%
- Category matching (Google Books disciplines): 15%
- User preferences (Firestore profile alignment): 15%
- Reading-level relevance (Beginner, Intermediate, Advanced): 10%

Provides grounded RAG explanations, natural language parsing, and vector-accelerated
candidate ranking.
"""

import re
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.google_books_service import GoogleBooksService
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore
from services.semantic_search_service import SemanticSearchService
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Category Keyword Mapping
CATEGORY_KEYWORDS = {
    "Programming": [
        "programming", "code", "coding", "software", "python", "javascript", "java",
        "c++", "c#", "rust", "golang", "web development", "backend", "frontend",
        "full stack", "react", "html", "css", "node", "django", "flask", "algorithms",
    ],
    "Artificial Intelligence": [
        "artificial intelligence", "ai", "deep learning", "neural network",
        "computer vision", "nlp", "natural language processing", "generative ai",
        "reinforcement learning", "robotics",
    ],
    "Machine Learning": [
        "machine learning", "ml", "supervised learning", "classification",
        "regression", "scikit-learn", "tensorflow", "pytorch", "predictive modeling",
    ],
    "Data Science": [
        "data science", "data analysis", "big data", "analytics", "statistics",
        "pandas", "data visualization", "sql", "business intelligence",
    ],
    "Science": [
        "science", "physics", "chemistry", "biology", "astronomy", "quantum",
        "cosmology", "genetics", "neuroscience", "scientific",
    ],
    "Technology": [
        "technology", "tech", "computing", "cloud", "aws", "cybersecurity",
        "devops", "internet", "hardware", "iot", "blockchain", "networks",
    ],
    "Fiction": [
        "fiction", "novel", "story", "stories", "fantasy", "scifi", "sci-fi",
        "science fiction", "drama", "literature",
    ],
    "Mystery": [
        "mystery", "detective", "crime", "investigation", "sherlock", "whodunit",
        "murder", "suspense",
    ],
    "Thriller": [
        "thriller", "psychological thriller", "action", "espionage", "spy",
        "intrigue", "suspense",
    ],
    "History": [
        "history", "historical", "war", "civilization", "ancient", "medieval",
        "world war", "empire", "revolution",
    ],
    "Business": [
        "business", "entrepreneurship", "finance", "economics", "investing",
        "startup", "management", "leadership", "marketing", "sales", "wealth",
    ],
    "Self-help": [
        "self-help", "productivity", "habit", "mindset", "motivation", "success",
        "mental health", "happiness", "discipline", "personal growth",
    ],
    "Biography": [
        "biography", "memoir", "autobiography", "life story", "diary",
    ],
    "Education": [
        "education", "student", "study", "learning", "teaching", "pedagogy",
        "academic", "textbook", "exam", "school", "university",
    ],
}

# Level Keywords
LEVEL_PATTERNS = {
    "Beginner to Advanced": [
        r"beginner\s+to\s+advanced",
        r"zero\s+to\s+hero",
        r"scratch\s+to\s+expert",
        r"complete\s+guide",
        r"mastery\s+from\s+basics",
    ],
    "Beginner": [
        r"\bbeginner\b",
        r"\bbeginners\b",
        r"\bbasics?\b",
        r"\bintroduction\b",
        r"\bintroductory\b",
        r"\bfundamentals?\b",
        r"\bfor\s+dummies\b",
        r"\bnovice\b",
        r"\b101\b",
        r"\bstarting\b",
    ],
    "Intermediate": [
        r"\bintermediate\b",
        r"\bpractical\b",
        r"\bhands-on\b",
        r"\bapplied\b",
        r"\bworking\s+knowledge\b",
    ],
    "Advanced": [
        r"\badvanced\b",
        r"\bexpert\b",
        r"\bdeep\s+dive\b",
        r"\bin-depth\b",
        r"\bprofessional\b",
        r"\barchitecture\b",
        r"\bcomplex\b",
        r"\badvanced\s+topics\b",
    ],
}

PURPOSE_PATTERNS = {
    "Learning / Educational": ["learn", "study", "understand", "textbook", "course", "curriculum", "master", "guide"],
    "Career & Professional Development": ["career", "interview", "job", "work", "industry", "professional", "portfolio"],
    "Research & Academic": ["research", "thesis", "academic", "theory", "paper", "scientific", "study"],
    "Leisure & Personal Interest": ["enjoy", "relax", "novel", "fun", "hobby", "fiction", "read for pleasure"],
}


class NaturalLanguageQueryParser:
    """Parses natural-language user queries into structured search criteria."""

    @classmethod
    def parse(cls, query: str) -> Dict[str, Any]:
        raw = query.strip()
        lower_q = raw.lower()

        # 1. Detect Requested Number of Books (e.g. "top 5", "5 books", "10 recommendations")
        requested_count = 10
        num_match = re.search(r"\b(top\s+|recommend\s+|give\s+me\s+)?(\d{1,2})\b\s*(books|recommendations)?", lower_q)
        if num_match:
            try:
                found_num = int(num_match.group(2))
                if 1 <= found_num <= 30:
                    requested_count = found_num
            except (ValueError, TypeError):
                pass

        # 2. Detect Author if pattern "by [Author Name]" exists
        preferred_author = None
        author_match = re.search(r"\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", raw)
        if author_match:
            preferred_author = author_match.group(1)

        # 3. Detect Reading Level
        detected_level = "All Levels"
        for level, patterns in LEVEL_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, lower_q):
                    detected_level = level
                    break
            if detected_level != "All Levels":
                break

        # 4. Detect Purpose
        detected_purpose = "Learning & Discovery"
        for purpose, keywords in PURPOSE_PATTERNS.items():
            if any(k in lower_q for k in keywords):
                detected_purpose = purpose
                break

        # 5. Detect Category & Subject
        detected_category = "General"
        best_cat_matches = 0
        matched_category = None

        for cat, kws in CATEGORY_KEYWORDS.items():
            matches = sum(1 for kw in kws if re.search(rf"\b{re.escape(kw)}\b", lower_q))
            if matches > best_cat_matches:
                best_cat_matches = matches
                matched_category = cat

        if matched_category:
            detected_category = matched_category

        # 6. Extract core subject keywords (remove common filler phrases)
        cleaned_subject = re.sub(
            r"\b(i\s+want\s+to|recommend\s+books|recommend\s+me|suggest\s+some|suggest|books\s+for|books\s+about|"
            r"show\s+me|find\s+me|beginner\s+to\s+advanced|for\s+beginners|from\s+beginner\s+to\s+advanced|"
            r"top\s+\d+|give\s+me|please|looking\s+for)\b",
            "",
            lower_q,
        ).strip()
        cleaned_subject = re.sub(r"\s+", " ", cleaned_subject).strip()

        if not cleaned_subject:
            cleaned_subject = detected_category if detected_category != "General" else query

        return {
            "original_query": query,
            "subject": cleaned_subject.title(),
            "category": detected_category,
            "reading_level": detected_level,
            "purpose": detected_purpose,
            "preferred_author": preferred_author,
            "requested_count": requested_count,
        }


class RecommendationEngine:
    """Hybrid Recommendation Engine using Sentence Transformers, FAISS, and Multi-Factor Scoring with TTL Caching."""

    _rec_cache_lock = threading.Lock()
    _rec_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _REC_CACHE_TTL = 900  # 15 minutes TTL for identical queries and preferences

    @classmethod
    def _compute_text_similarity(cls, text_a: str, text_b: str) -> float:
        """Computes TF-IDF Cosine Similarity between two text passages."""
        if not text_a.strip() or not text_b.strip():
            return 0.1
        try:
            tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            matrix = tfidf.fit_transform([text_a, text_b])
            sim = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
            return float(np.clip(sim, 0.0, 1.0))
        except Exception:
            set_a = set(re.findall(r"\w+", text_a.lower()))
            set_b = set(re.findall(r"\w+", text_b.lower()))
            if not set_a or not set_b:
                return 0.1
            return float(len(set_a & set_b) / len(set_a | set_b))

    @classmethod
    def _score_reading_level(cls, target_level: str, book: Dict[str, Any]) -> float:
        """Determines reading level alignment based on actual metadata."""
        if target_level == "All Levels":
            return 0.85

        combined_text = f"{book.get('title', '')} {book.get('subtitle', '')} {book.get('description', '')}".lower()
        level_target = target_level.lower()

        if "beginner" in level_target or "basics" in level_target:
            if any(w in combined_text for w in ["beginner", "intro", "basics", "fundamentals", "starter", "dummies"]):
                return 1.0
            if any(w in combined_text for w in ["advanced", "complex", "research", "architecture"]):
                return 0.3
            return 0.65

        if "advanced" in level_target:
            if any(w in combined_text for w in ["advanced", "mastering", "expert", "deep dive", "in-depth", "architecture"]):
                return 1.0
            if any(w in combined_text for w in ["for dummies", "beginner", "basics 101"]):
                return 0.3
            return 0.65

        if "intermediate" in level_target:
            if any(w in combined_text for w in ["practical", "hands-on", "intermediate", "cookbook", "action"]):
                return 1.0
            return 0.7

        return 0.8

    @classmethod
    def _score_category(cls, target_category: str, book: Dict[str, Any]) -> float:
        """Calculates category matching score."""
        if target_category == "General":
            return 0.75

        book_cats = [c.lower() for c in book.get("categories", [])]
        target_cat_lower = target_category.lower()

        for c in book_cats:
            if target_cat_lower in c or c in target_cat_lower:
                return 1.0

        keywords = CATEGORY_KEYWORDS.get(target_category, [])
        book_blob = f"{book.get('title', '')} {book.get('description', '')}".lower()
        match_count = sum(1 for kw in keywords if kw in book_blob)
        if match_count >= 3:
            return 0.85
        elif match_count >= 1:
            return 0.65

        return 0.35

    @classmethod
    def _score_user_preferences(cls, user_preferences: List[str], book: Dict[str, Any]) -> float:
        """Calculates matching against the user's stored favourite categories."""
        if not user_preferences:
            return 0.8  # Neutral baseline when preferences are unconfigured

        book_cats = [c.lower() for c in book.get("categories", [])]
        for pref in user_preferences:
            pref_lower = pref.lower()
            if any(pref_lower in c for c in book_cats):
                return 1.0

            kws = CATEGORY_KEYWORDS.get(pref, [])
            desc = (book.get("description") or "").lower()
            if any(kw in desc for kw in kws):
                return 0.85

        return 0.45

    @classmethod
    def _generate_explanation(
        cls,
        book: Dict[str, Any],
        parsed: Dict[str, Any],
        final_score: float,
    ) -> str:
        """Generates an honest, metadata-backed explanation."""
        return LLMService.generate_grounded_explanation(
            book=book,
            query=parsed.get("original_query", ""),
            query_analysis=parsed,
        )

    @classmethod
    def get_recommendations(
        cls,
        query: str,
        user_preferences: Optional[List[str]] = None,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Hybrid Recommendation Algorithm.
        
        Scoring Weights:
        - Semantic Similarity (Sentence Transformers + FAISS): 35%
        - Subject Relevance (n-gram / keyword overlap): 25%
        - Category Matching: 15%
        - User Preferences: 15%
        - Reading-Level Relevance: 10%
        """
        if user_preferences is None:
            user_preferences = []

        clean_query = query.strip()
        parsed = NaturalLanguageQueryParser.parse(clean_query)
        target_count = max_results or parsed.get("requested_count", 10)
        target_count = max(3, min(target_count, 25))

        # ── Check In-Memory Cache for Instant Return ──
        cache_key = f"{clean_query}|{','.join(sorted(user_preferences))}|{target_count}"
        with cls._rec_cache_lock:
            cached = cls._rec_cache.get(cache_key)
            if cached and (time.time() - cached[0] < cls._REC_CACHE_TTL):
                return cached[1]

        subject = parsed["subject"]
        category = parsed["category"]
        reading_level = parsed["reading_level"]

        # 1. Retrieve Candidate Books from Google Books API
        search_terms = []
        if subject:
            search_terms.append(subject)
        if category != "General":
            search_terms.append(f'subject:"{category}"')
        if parsed.get("preferred_author"):
            search_terms.append(f'inauthor:"{parsed["preferred_author"]}"')

        combined_api_query = " ".join(search_terms) if search_terms else clean_query

        api_res = GoogleBooksService.search_books(
            query=combined_api_query,
            max_results=35,
            sort_by="relevance",
        )
        candidates = api_res.get("books", [])

        if not candidates and subject:
            fallback_res = GoogleBooksService.search_books(query=subject, max_results=30)
            candidates = fallback_res.get("books", [])

        # 2. Vector Indexing into FAISS
        SemanticSearchService.index_books(candidates)

        # 3. Compute Query Embedding & FAISS Semantic Similarity
        query_vec = EmbeddingService.get_embedding(clean_query)
        vector_store = VectorStore()
        candidate_ids = [b.get("id") or b.get("googleBookId") for b in candidates if (b.get("id") or b.get("googleBookId"))]

        faiss_matches = vector_store.search(
            query_embedding=query_vec,
            top_k=len(candidate_ids) if candidate_ids else 30,
            filter_volume_ids=candidate_ids if candidate_ids else None,
        )
        semantic_sim_map = {}
        for b, sim in faiss_matches:
            vid = b.get("id") or b.get("googleBookId", "")
            if vid:
                semantic_sim_map[vid] = sim

        # 4. Multi-Factor Hybrid Scoring
        ranked_books = []
        for book in candidates:
            volume_id = book.get("id") or book.get("googleBookId", "")

            # Factor 1: Semantic similarity (35%) from Sentence Transformers & FAISS
            semantic_sim = semantic_sim_map.get(volume_id)
            if semantic_sim is None:
                book_vec = EmbeddingService.embed_book(book)
                semantic_sim = EmbeddingService.compute_similarity(query_vec, book_vec)

            # Factor 2: Subject relevance (25%)
            title_text = f"{book.get('title', '')} {book.get('subtitle', '')}"
            subject_sim = cls._compute_text_similarity(subject, title_text)
            if subject.lower() in title_text.lower():
                subject_sim = max(subject_sim, 0.90)

            # Factor 3: Category matching (15%)
            cat_score = cls._score_category(category, book)

            # Factor 4: User preferences (15%)
            user_pref_score = cls._score_user_preferences(user_preferences, book)

            # Factor 5: Reading-level relevance (10%)
            level_score = cls._score_reading_level(reading_level, book)

            # Composite Formula:
            # (0.35 * Semantic) + (0.25 * Subject) + (0.15 * Category) + (0.15 * UserPref) + (0.10 * ReadingLevel)
            raw_score = (
                (0.35 * semantic_sim)
                + (0.25 * subject_sim)
                + (0.15 * cat_score)
                + (0.15 * user_pref_score)
                + (0.10 * level_score)
            )

            if book.get("rating") and book.get("rating") >= 4.5:
                raw_score += 0.03

            score_percent = int(round(raw_score * 100))
            score_percent = max(40, min(score_percent, 99))

            explanation = cls._generate_explanation(book, parsed, score_percent)

            book_copy = dict(book)
            book_copy["recommendation_score"] = score_percent
            book_copy["recommendation_reason"] = explanation
            book_copy["semantic_similarity"] = float(round(semantic_sim, 4))
            book_copy["score_breakdown"] = {
                "semantic_similarity": int(round(semantic_sim * 100)),
                "subject_relevance": int(round(subject_sim * 100)),
                "category_matching": int(round(cat_score * 100)),
                "user_preference": int(round(user_pref_score * 100)),
                "reading_level": int(round(level_score * 100)),
            }
            ranked_books.append(book_copy)

        # 5. Rank books descending by recommendation score
        ranked_books.sort(key=lambda b: b.get("recommendation_score", 0), reverse=True)
        final_recommendations = ranked_books[:target_count]

        result = {
            "success": True,
            "query_analysis": parsed,
            "recommendations": final_recommendations,
            "total_found": len(final_recommendations),
            "algorithm": {
                "type": "Hybrid AI Recommendation Engine",
                "weights": {
                    "semantic_similarity": "35%",
                    "subject_relevance": "25%",
                    "category_matching": "15%",
                    "user_preferences": "15%",
                    "reading_level": "10%",
                },
                "models": {
                    "embeddings": "Sentence Transformers (all-MiniLM-L6-v2)",
                    "vector_db": "FAISS (IndexFlatIP)",
                    "llm": "Ollama (Local)" if LLMService.is_available() else "Grounded Heuristics",
                },
            },
        }

        with cls._rec_cache_lock:
            cls._rec_cache[cache_key] = (time.time(), result)

        return result
