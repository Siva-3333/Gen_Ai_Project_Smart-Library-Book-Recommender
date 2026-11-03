"""Book Discovery, Exploration, and Details Routes.

Handles the home page, explore page, book details page,
and JSON APIs powered by Google Books API.
"""

import concurrent.futures
from flask import Blueprint, current_app, jsonify, render_template, request, session
from services.google_books_service import GoogleBooksService
from services.firebase_service import FirebaseService

book_bp = Blueprint("books", __name__)


@book_bp.route("/")
def index():
    """Home landing page & personalized dashboard preview."""
    user = session.get("user")
    categories = current_app.config.get("CATEGORIES", [])

    # Fetch curated books for home sections concurrently in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        f_trending = executor.submit(
            GoogleBooksService.search_books,
            query="bestseller technology fiction",
            max_results=8,
        )
        f_popular = executor.submit(
            GoogleBooksService.search_books,
            query="computer science artificial intelligence",
            max_results=8,
        )
        f_recent = executor.submit(
            GoogleBooksService.search_books,
            query="data science machine learning",
            max_results=8,
            sort_by="newest",
        )

        trending_res = f_trending.result()
        popular_res = f_popular.result()
        recent_res = f_recent.result()

    trending_books = trending_res.get("books", [])
    popular_books = popular_res.get("books", [])
    recent_books = recent_res.get("books", [])

    # If user is authenticated, fetch their "continue reading" books from Firestore
    continue_reading = []
    if user and user.get("uid"):
        user_lib = FirebaseService.get_user_library(user["uid"], status_filter="currently_reading")
        continue_reading = user_lib[:6]

    return render_template(
        "index.html",
        categories=categories,
        trending_books=trending_books,
        popular_books=popular_books,
        recent_books=recent_books,
        continue_reading=continue_reading,
        user=user,
    )


@book_bp.route("/explore")
def explore():
    """Dedicated book exploration page with multi-facet filters and pagination."""
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "All").strip()
    search_field = request.args.get("field", "all").strip()
    sort_by = request.args.get("sort", "relevance").strip()

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        max_results = min(40, max(6, int(request.args.get("limit", 16))))
    except (ValueError, TypeError):
        max_results = 16

    start_index = (page - 1) * max_results

    # Search Google Books API
    api_res = GoogleBooksService.search_books(
        query=query if query else (f"subject:{category}" if category != "All" else "technology"),
        category=category if category != "All" else None,
        max_results=max_results,
        start_index=start_index,
        sort_by=sort_by,
        search_field=search_field,
    )

    books = api_res.get("books", [])
    total_items = api_res.get("total_items", 0)
    total_pages = min(20, (total_items + max_results - 1) // max_results) if total_items > 0 else 1

    # Log search history if user is logged in and query is non-empty
    user = session.get("user")
    if user and user.get("uid") and query:
        FirebaseService.log_search(user["uid"], query)

    return render_template(
        "explore.html",
        books=books,
        query=query,
        selected_category=category,
        search_field=search_field,
        sort_by=sort_by,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        categories=current_app.config.get("CATEGORIES", []),
    )


@book_bp.route("/book/<book_id>")
def book_details(book_id):
    """Book Details page with comprehensive metadata, reviews, and related books."""
    book = GoogleBooksService.get_book_details(book_id)
    if not book:
        return render_template("404.html", message="Book not found or temporarily unavailable."), 404

    # Log recently viewed book and retrieve user shelf status if authenticated
    user = session.get("user")
    user_library_entry = None
    if user and user.get("uid"):
        FirebaseService.log_book_view(user["uid"], book)
        user_books = FirebaseService.get_user_library(user["uid"], status_filter="all")
        user_library_entry = next((b for b in user_books if b.get("googleBookId") == book_id), None)

    # Fetch community reviews from Firestore
    reviews_data = FirebaseService.get_book_reviews(book_id)

    # Fetch related books in the same primary category
    related_books = []
    primary_category = book.get("category", "General")
    if primary_category and primary_category != "General":
        rel_res = GoogleBooksService.search_books(query=f'subject:"{primary_category}"', max_results=6)
        related_books = [b for b in rel_res.get("books", []) if b.get("id") != book_id][:5]

    return render_template(
        "book_details.html",
        book=book,
        reviews=reviews_data.get("reviews", []),
        average_rating=reviews_data.get("average_rating", 0.0),
        total_reviews=reviews_data.get("total_reviews", 0),
        related_books=related_books,
        user=user,
        user_library_entry=user_library_entry,
    )


@book_bp.route("/book/<book_id>/read")
def book_reader(book_id):
    """Full-screen interactive digital book reader studio with Google Viewer and PDF.js."""
    book = GoogleBooksService.get_book_details(book_id)
    if not book:
        return render_template("404.html", message="Book not found or temporarily unavailable."), 404

    user = session.get("user")
    user_library_entry = None
    if user and user.get("uid"):
        FirebaseService.log_book_view(user["uid"], book)
        user_books = FirebaseService.get_user_library(user["uid"], status_filter="all")
        user_library_entry = next((b for b in user_books if b.get("googleBookId") == book_id), None)

    return render_template(
        "book_reader.html",
        book=book,
        user=user,
        user_library_entry=user_library_entry,
    )


@book_bp.route("/api/books/search")
def api_search_books():
    """AJAX endpoint for instant book search and typeahead."""
    query = request.args.get("q", "").strip()
    category = request.args.get("category")
    max_results = min(40, int(request.args.get("limit", 12)))
    sort_by = request.args.get("sort", "relevance")

    res = GoogleBooksService.search_books(
        query=query,
        category=category,
        max_results=max_results,
        sort_by=sort_by,
    )
    return jsonify(res)


@book_bp.route("/api/books/<book_id>")
def api_get_book(book_id):
    """AJAX endpoint to get single book metadata."""
    book = GoogleBooksService.get_book_details(book_id)
    if not book:
        return jsonify({"success": False, "message": "Book not found"}), 404
    return jsonify({"success": True, "book": book})

