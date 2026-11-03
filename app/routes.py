import requests
from flask import Blueprint, render_template, request, jsonify, current_app
from app.firebase import get_db

main = Blueprint("main", __name__)

BOOKS_API_BASE = "https://www.googleapis.com/books/v1/volumes"


def search_books(query: str, max_results: int = 20) -> list[dict]:
    """Query the Google Books API and return a list of book dicts."""
    api_key = current_app.config["GOOGLE_BOOKS_API_KEY"]
    params = {
        "q": query,
        "maxResults": max_results,
        "printType": "books",
        "key": api_key,
    }
    resp = requests.get(BOOKS_API_BASE, params=params, timeout=10)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    books = []
    for item in items:
        info = item.get("volumeInfo", {})
        books.append(
            {
                "id": item.get("id"),
                "title": info.get("title", "Unknown Title"),
                "authors": info.get("authors", ["Unknown Author"]),
                "description": info.get("description", ""),
                "thumbnail": info.get("imageLinks", {}).get("thumbnail", ""),
                "published": info.get("publishedDate", ""),
                "categories": info.get("categories", []),
                "rating": info.get("averageRating"),
                "page_count": info.get("pageCount"),
                "preview_link": info.get("previewLink", ""),
            }
        )
    return books


def get_book_by_id(book_id: str) -> dict | None:
    """Fetch a single book's details from the Google Books API."""
    api_key = current_app.config["GOOGLE_BOOKS_API_KEY"]
    resp = requests.get(
        f"{BOOKS_API_BASE}/{book_id}",
        params={"key": api_key},
        timeout=10,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    item = resp.json()
    info = item.get("volumeInfo", {})
    return {
        "id": item.get("id"),
        "title": info.get("title", "Unknown Title"),
        "authors": info.get("authors", ["Unknown Author"]),
        "description": info.get("description", ""),
        "thumbnail": info.get("imageLinks", {}).get("thumbnail", ""),
        "published": info.get("publishedDate", ""),
        "categories": info.get("categories", []),
        "rating": info.get("averageRating"),
        "ratings_count": info.get("ratingsCount"),
        "page_count": info.get("pageCount"),
        "language": info.get("language", ""),
        "preview_link": info.get("previewLink", ""),
        "publisher": info.get("publisher", ""),
    }


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@main.route("/")
def index():
    query = request.args.get("q", "").strip()
    books = []
    error = None
    if query:
        try:
            books = search_books(query)
        except Exception as exc:
            error = str(exc)
    return render_template("index.html", books=books, query=query, error=error)


@main.route("/book/<book_id>")
def book_detail(book_id):
    book = get_book_by_id(book_id)
    if book is None:
        return render_template("404.html"), 404
    return render_template("book.html", book=book)


# ---------------------------------------------------------------------------
# API / AJAX routes
# ---------------------------------------------------------------------------

@main.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400
    try:
        books = search_books(query)
        return jsonify({"results": books})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@main.route("/api/favourites", methods=["POST"])
def add_favourite():
    """Save a book to the signed-in user's Firestore favourites collection."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("userId")
    book_id = data.get("bookId")
    if not user_id or not book_id:
        return jsonify({"error": "userId and bookId are required"}), 400

    db = get_db()
    db.collection("users").document(user_id).collection("favourites").document(
        book_id
    ).set({"bookId": book_id, "addedAt": firestore.SERVER_TIMESTAMP})
    return jsonify({"success": True})


@main.route("/api/favourites/<user_id>")
def get_favourites(user_id):
    """Return the list of favourite book IDs for a user."""
    db = get_db()
    docs = (
        db.collection("users").document(user_id).collection("favourites").stream()
    )
    fav_ids = [doc.id for doc in docs]
    return jsonify({"favourites": fav_ids})

