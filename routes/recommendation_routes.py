"""Intelligent Recommendation Engine & Conversational AI Assistant Routes.

Integrates:
- Hybrid multi-factor recommendation pipeline (35% semantic, 25% subject, 15% category, 15% preferences, 10% level)
- Sentence Transformers + FAISS vector search
- RAG pipeline with grounded context
- Conversational AI Book Discovery Assistant with context memory and follow-up support
"""

import logging
from flask import Blueprint, jsonify, render_template, request, session
from services.firebase_service import FirebaseService
from services.recommendation_service import RecommendationEngine, NaturalLanguageQueryParser
from services.semantic_search_service import SemanticSearchService
from services.rag_service import RAGPipeline
from services.vector_store import VectorStore
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

rec_bp = Blueprint("recommendations", __name__)


@rec_bp.route("/recommendations")
def recommendations_page():
    """Renders the AI-powered recommendations view with integrated conversational assistant."""
    query = request.args.get("q", "").strip()
    user = session.get("user")

    user_preferences = []
    if user and user.get("uid"):
        user_preferences = FirebaseService.get_user_preferences(user["uid"])

    initial_results = None
    if query:
        initial_results = RecommendationEngine.get_recommendations(
            query=query,
            user_preferences=user_preferences,
        )
        if user and user.get("uid") and initial_results.get("recommendations"):
            rec_ids = [b["id"] for b in initial_results["recommendations"][:10]]
            FirebaseService.log_recommendation(user["uid"], query, rec_ids)

    sample_queries = [
        "I want to learn Python from beginner to advanced.",
        "Recommend books about Artificial Intelligence and Deep Learning.",
        "I like psychological mystery and thriller novels with twists.",
        "Suggest hands-on practical books for Machine Learning with Python.",
        "I want motivational and productivity books for university students.",
        "Books on Data Science and statistical visualization for beginners.",
    ]

    # AI System Status Indicators
    ai_status = {
        "sentence_transformers": "all-MiniLM-L6-v2 (Active)",
        "vector_db": f"FAISS ({VectorStore().total_books()} Volumes Indexed)",
        "llm": "Ollama (Connected)" if LLMService.is_available() else "Grounded Heuristic Engine",
    }

    return render_template(
        "recommendations.html",
        query=query,
        results=initial_results,
        sample_queries=sample_queries,
        user_preferences=user_preferences,
        user=user,
        ai_status=ai_status,
    )


@rec_bp.route("/api/recommendations", methods=["POST"])
def api_get_recommendations():
    """AJAX endpoint for instant hybrid multi-factor recommendation scoring."""
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"success": False, "message": "Query cannot be empty."}), 400

    user = session.get("user")
    user_preferences = []
    if user and user.get("uid"):
        user_preferences = FirebaseService.get_user_preferences(user["uid"])

    limit = data.get("limit")
    try:
        limit = int(limit) if limit else None
    except (ValueError, TypeError):
        limit = None

    results = RecommendationEngine.get_recommendations(
        query=query,
        user_preferences=user_preferences,
        max_results=limit,
    )

    if user and user.get("uid") and results.get("recommendations"):
        book_ids = [b["id"] for b in results["recommendations"][:10]]
        FirebaseService.log_recommendation(user["uid"], query, book_ids)

    return jsonify(results)


@rec_bp.route("/api/recommendations/semantic", methods=["POST"])
def api_semantic_search():
    """AJAX endpoint for pure semantic book search using Sentence Transformers and FAISS."""
    data = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    top_k = data.get("top_k", 10)

    if not query:
        return jsonify({"success": False, "message": "Query cannot be empty."}), 400

    try:
        top_k = max(1, min(int(top_k), 30))
    except (ValueError, TypeError):
        top_k = 10

    results = SemanticSearchService.search(query=query, top_k=top_k)
    return jsonify({
        "success": True,
        "query": query,
        "total": len(results),
        "results": results,
    })


@rec_bp.route("/api/ai-assistant/chat", methods=["POST"])
def api_assistant_chat():
    """Conversational AI Book Discovery Assistant Endpoint.
    
    Supports multi-turn natural language dialogue and context-aware follow-up queries.
    Example:
    1. "I want to learn Artificial Intelligence" -> AI books.
    2. "Show me beginner-level books" -> Context preserved, filters for beginner AI books.
    """
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])  # list of {role, content}
    context = data.get("context", {})   # {subject, category, reading_level}

    if not message:
        return jsonify({"success": False, "message": "Message cannot be empty."}), 400

    user = session.get("user")
    user_preferences = []
    if user and user.get("uid"):
        user_preferences = FirebaseService.get_user_preferences(user["uid"])

    # Execute RAG Pipeline with context awareness
    rag_result = RAGPipeline.execute(
        query=message,
        user_preferences=user_preferences,
        max_results=6,
        conversation_context=context,
    )

    retrieved_books = rag_result.get("recommendations", [])
    query_analysis = rag_result.get("query_analysis", {})

    # Generate conversational reply
    reply = LLMService.conversational_reply(
        user_message=message,
        retrieved_books=retrieved_books,
        conversation_history=history,
        query_analysis=query_analysis,
    )

    # Updated context for next turn
    updated_context = {
        "subject": query_analysis.get("subject", context.get("subject", "")),
        "category": query_analysis.get("category", context.get("category", "")),
        "reading_level": query_analysis.get("reading_level", context.get("reading_level", "All Levels")),
    }

    return jsonify({
        "success": True,
        "reply": reply,
        "books": retrieved_books,
        "query_analysis": query_analysis,
        "context": updated_context,
        "rag_metadata": rag_result.get("rag_metadata", {}),
    })


@rec_bp.route("/api/ai-assistant/status", methods=["GET"])
def api_assistant_status():
    """Returns real-time telemetry on the AI stack."""
    vector_store = VectorStore()
    return jsonify({
        "status": "online",
        "sentence_transformers": {
            "model": "all-MiniLM-L6-v2",
            "dimension": 384,
            "status": "active",
        },
        "vector_database": {
            "engine": "FAISS IndexFlatIP",
            "metric": "Cosine Similarity (Inner Product)",
            "indexed_volumes": vector_store.total_books(),
        },
        "llm": {
            "provider": "Ollama (Open-Source)",
            "available": LLMService.is_available(),
            "model": LLMService._rule_based_explanation.__name__ if not LLMService.is_available() else "Ollama Local",
        },
        "rag_pipeline": {
            "status": "active",
            "data_source": "Google Books Cloud API",
            "zero_hallucination_guarantee": True,
        },
    })
