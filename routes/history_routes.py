"""Search and Reading History Routes.

Provides full visibility into past search queries, previous recommendations,
and ability to re-run searches or clear history logs.
"""

from flask import Blueprint, jsonify, render_template, session
from routes.auth_routes import login_required
from services.firebase_service import FirebaseService
from services.google_books_service import GoogleBooksService

history_bp = Blueprint("history", __name__)


@history_bp.route("/history")
@login_required
def history_page():
    """Renders the comprehensive search and recommendation history log."""
    user = session["user"]
    uid = user["uid"]

    searches = FirebaseService.get_user_search_history(uid, limit=30)
    rec_history = FirebaseService.get_recommendation_history(uid, limit=10)

    # For recommendation history, fetch preview thumbnails
    enriched_recs = []
    for entry in rec_history:
        book_ids = entry.get("recommendedBookIds", [])[:4]
        preview_books = []
        for b_id in book_ids:
            b = GoogleBooksService.get_book_details(b_id)
            if b:
                preview_books.append(b)
        enriched_recs.append({
            "query": entry.get("searchQuery", ""),
            "createdAt": entry.get("createdAt", ""),
            "books": preview_books,
        })

    return render_template(
        "history.html",
        searches=searches,
        recommendation_history=enriched_recs,
        user=user,
    )


@history_bp.route("/api/history/clear", methods=["POST"])
@login_required
def clear_history():
    """Clear all past search queries for the active user."""
    uid = session["user"]["uid"]
    success = FirebaseService.clear_search_history(uid)
    if success:
        return jsonify({"success": True, "message": "Search history has been cleared."})
    return jsonify({"success": False, "message": "Failed to clear search history."}), 500

