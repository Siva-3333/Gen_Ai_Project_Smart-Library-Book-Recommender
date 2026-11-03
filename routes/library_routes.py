"""Personal Digital Library Routes.

Handles user's reading lists:
- Want to Read
- Currently Reading
- Completed Books
Provides duplicate-checked additions, status transitions, and search.
"""

from flask import Blueprint, jsonify, render_template, request, session
from routes.auth_routes import login_required
from services.firebase_service import FirebaseService
from services.google_books_service import GoogleBooksService

library_bp = Blueprint("library", __name__)


@library_bp.route("/my-library")
@login_required
def my_library_page():
    """Renders the personal digital library dashboard."""
    user = session["user"]
    uid = user["uid"]

    status_filter = request.args.get("status", "all")
    books = FirebaseService.get_user_library(uid, status_filter=status_filter)
    stats = FirebaseService.get_library_statistics(uid)

    return render_template(
        "my_library.html",
        books=books,
        stats=stats,
        current_filter=status_filter,
        user=user,
    )


@library_bp.route("/api/library", methods=["GET"])
@login_required
def api_get_library():
    uid = session["user"]["uid"]
    status_filter = request.args.get("status", "all")
    books = FirebaseService.get_user_library(uid, status_filter=status_filter)
    return jsonify({"success": True, "books": books, "count": len(books)})


@library_bp.route("/api/library", methods=["POST"])
@login_required
def api_add_to_library():
    uid = session["user"]["uid"]
    data = request.get_json(silent=True) or {}
    google_book_id = data.get("bookId")
    reading_status = data.get("status", "want_to_read")

    if not google_book_id:
        return jsonify({"success": False, "message": "Book ID is required"}), 400

    # Retrieve official book details to store clean reference in library
    book = GoogleBooksService.get_book_details(google_book_id)
    if not book:
        # Fallback to book details provided in payload if Google Books API is unreachable
        book = {
            "title": data.get("title", "Untitled"),
            "authors": data.get("authors", ["Not available"]),
            "thumbnail": data.get("thumbnail", ""),
            "category": data.get("category", "General"),
            "rating": data.get("rating"),
        }

    res = FirebaseService.add_to_library(
        uid=uid,
        google_book_id=google_book_id,
        book_data=book,
        reading_status=reading_status,
    )
    return jsonify(res)


@library_bp.route("/api/library/status", methods=["PUT"])
@login_required
def api_update_status():
    uid = session["user"]["uid"]
    data = request.get_json(silent=True) or {}
    google_book_id = data.get("bookId")
    new_status = data.get("status")

    if not google_book_id or not new_status:
        return jsonify({"success": False, "message": "Book ID and status are required"}), 400

    success = FirebaseService.update_reading_status(uid, google_book_id, new_status)
    if success:
        return jsonify({"success": True, "message": f"Reading status updated to '{new_status.replace('_', ' ').title()}'."})
    return jsonify({"success": False, "message": "Failed to update reading status."}), 400


@library_bp.route("/api/library/progress", methods=["POST", "PUT"])
@login_required
def api_update_progress():
    """Updates or increments page reading progress (e.g. Page 7, 8, etc.)."""
    uid = session["user"]["uid"]
    data = request.get_json(silent=True) or {}
    google_book_id = data.get("bookId")
    action = data.get("action", "set")  # "increment" or "set"

    if not google_book_id:
        return jsonify({"success": False, "message": "Book ID is required"}), 400

    total_pages = data.get("totalPages")

    if action == "increment":
        # Get existing library entry
        user_books = FirebaseService.get_user_library(uid, status_filter="all")
        target_book = next((b for b in user_books if b.get("googleBookId") == google_book_id), None)
        if not target_book:
            # Auto-save book to library as currently_reading starting at page 1
            book_details = GoogleBooksService.get_book_details(google_book_id) or {}
            add_res = FirebaseService.add_to_library(uid, google_book_id, book_details, reading_status="currently_reading")
            target_book = add_res.get("item", {})

        current_page = int(target_book.get("currentPage", 0)) + 1
        if not total_pages:
            total_pages = target_book.get("pageCount")
    else:
        try:
            current_page = max(0, int(data.get("currentPage", 0)))
        except (ValueError, TypeError):
            current_page = 0

    res = FirebaseService.update_reading_progress(
        uid=uid,
        google_book_id=google_book_id,
        current_page=current_page,
        total_pages=total_pages,
    )
    return jsonify(res)


@library_bp.route("/api/library/<google_book_id>", methods=["DELETE"])
@login_required
def api_remove_from_library(google_book_id):
    uid = session["user"]["uid"]
    success = FirebaseService.remove_from_library(uid, google_book_id)
    if success:
        return jsonify({"success": True, "message": "Book removed from your library."})
    return jsonify({"success": False, "message": "Could not remove book from library."}), 400

