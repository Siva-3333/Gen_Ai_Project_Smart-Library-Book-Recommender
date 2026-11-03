"""User Profile, Personalized Dashboard, and Preferences Routes."""

import concurrent.futures
from flask import Blueprint, current_app, jsonify, render_template, request, session
from routes.auth_routes import login_required
from services.firebase_service import FirebaseService
from services.google_books_service import GoogleBooksService
from services.recommendation_service import RecommendationEngine

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/dashboard")
@login_required
def dashboard_page():
    """Renders the comprehensive personalized dashboard with parallel execution and caching."""
    user = session["user"]
    uid = user["uid"]

    # 1. Fetch user preferences (prefer session if present)
    fav_categories = user.get("favouriteCategories")
    if not fav_categories:
        fav_categories = FirebaseService.get_user_preferences(uid)
    if not fav_categories:
        fav_categories = ["Programming", "Technology"]

    # 2. Concurrently fetch library, recently viewed, and search history in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        f_lib = executor.submit(FirebaseService.get_user_library, uid, status_filter="all")
        f_recent = executor.submit(FirebaseService.get_recently_viewed, uid, limit=6)
        f_search = executor.submit(FirebaseService.get_user_search_history, uid, limit=5)

        all_user_books = f_lib.result()
        recently_viewed = f_recent.result()
        search_history = f_search.result()

    # 3. Derive statistics, continue reading, and recently saved in memory (0ms)
    continue_reading = [b for b in all_user_books if b.get("readingStatus") == "currently_reading"][:6]
    recently_saved = all_user_books[:6]
    stats = {
        "total_saved": len(all_user_books),
        "currently_reading": len(continue_reading),
        "completed": sum(1 for b in all_user_books if b.get("readingStatus") == "completed"),
        "want_to_read": sum(1 for b in all_user_books if b.get("readingStatus") == "want_to_read"),
    }

    # 4. Personalized Recommendations based on user's favourite categories (cached)
    rec_query = " ".join(fav_categories[:3])
    rec_res = RecommendationEngine.get_recommendations(
        query=rec_query,
        user_preferences=fav_categories,
        max_results=8,
    )
    recommended_books = rec_res.get("recommendations", [])

    return render_template(
        "dashboard.html",
        user=user,
        stats=stats,
        fav_categories=fav_categories,
        recommended_books=recommended_books,
        recently_viewed=recently_viewed,
        continue_reading=continue_reading,
        recently_saved=recently_saved,
        search_history=search_history,
    )


@profile_bp.route("/preferences")
@login_required
def preferences_page():
    """Renders the Category Preferences configuration page."""
    user = session["user"]
    uid = user["uid"]
    all_categories = current_app.config.get("CATEGORIES", [])
    user_preferences = FirebaseService.get_user_preferences(uid)

    return render_template(
        "preferences.html",
        user=user,
        all_categories=all_categories,
        user_preferences=user_preferences,
    )


@profile_bp.route("/api/user/preferences", methods=["POST"])
@login_required
def api_update_preferences():
    """Saves updated category preferences to Firestore and session."""
    uid = session["user"]["uid"]
    data = request.get_json(silent=True) or {}
    categories = data.get("categories", [])

    if not isinstance(categories, list):
        return jsonify({"success": False, "message": "Categories must be a list"}), 400

    success = FirebaseService.save_user_preferences(uid, categories)
    if success:
        session["user"]["favouriteCategories"] = categories
        session.modified = True
        return jsonify({"success": True, "message": "Preferences updated successfully!"})

    return jsonify({"success": False, "message": "Failed to update preferences."}), 500


@profile_bp.route("/profile")
@login_required
def profile_page():
    """Renders the user profile overview and settings."""
    user = session["user"]
    uid = user["uid"]
    stats = FirebaseService.get_library_statistics(uid)
    user_doc = FirebaseService.get_user_profile(uid) or {}

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        user_doc=user_doc,
    )


@profile_bp.route("/api/user/profile", methods=["POST"])
@login_required
def api_update_profile():
    """Updates user display name and profile image."""
    uid = session["user"]["uid"]
    data = request.get_json(silent=True) or {}
    full_name = data.get("fullName", "").strip()

    if not full_name:
        return jsonify({"success": False, "message": "Full name cannot be empty."}), 400

    update_payload = {"fullName": full_name}
    success = FirebaseService.update_user_profile(uid, update_payload)
    if success:
        session["user"]["displayName"] = full_name
        session.modified = True
        return jsonify({"success": True, "message": "Profile updated successfully!"})

    return jsonify({"success": False, "message": "Failed to update profile."}), 500

