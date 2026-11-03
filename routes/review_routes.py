"""Ratings and Reviews Routes.

Allows authenticated users to rate books (1-5 stars), post reviews,
edit their own reviews, and delete reviews, with community aggregation.
"""

from flask import Blueprint, jsonify, request, session
from routes.auth_routes import login_required
from services.firebase_service import FirebaseService

review_bp = Blueprint("reviews", __name__)


@review_bp.route("/api/reviews/<book_id>", methods=["GET"])
def get_reviews(book_id):
    """Retrieve community reviews and computed average for a given book."""
    data = FirebaseService.get_book_reviews(book_id)
    return jsonify({"success": True, **data})


@review_bp.route("/api/reviews/<book_id>", methods=["POST"])
@login_required
def submit_review(book_id):
    """Submit or update a rating and review for a book."""
    user = session["user"]
    uid = user["uid"]
    user_name = user.get("displayName", "Anonymous Reader")
    user_email = user.get("email", "")

    data = request.get_json(silent=True) or {}
    rating = data.get("rating")
    review_text = data.get("reviewText", "").strip()

    if not rating:
        return jsonify({"success": False, "message": "Rating (1 to 5 stars) is required."}), 400

    try:
        rating_int = int(rating)
        if not (1 <= rating_int <= 5):
            return jsonify({"success": False, "message": "Rating must be between 1 and 5."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid rating value."}), 400

    if not review_text:
        return jsonify({"success": False, "message": "Please write a few words about this book."}), 400

    if len(review_text) > 2000:
        return jsonify({"success": False, "message": "Review text is too long (max 2000 characters)."}), 400

    result = FirebaseService.add_or_update_review(
        uid=uid,
        user_name=user_name,
        user_email=user_email,
        google_book_id=book_id,
        rating=rating_int,
        review_text=review_text,
    )
    return jsonify(result)


@review_bp.route("/api/reviews/<book_id>", methods=["DELETE"])
@login_required
def delete_review(book_id):
    """Delete the authenticated user's review for a book."""
    uid = session["user"]["uid"]
    success = FirebaseService.delete_review(uid, book_id)
    if success:
        return jsonify({"success": True, "message": "Your review has been deleted."})
    return jsonify({"success": False, "message": "Could not delete review or review does not belong to you."}), 400

