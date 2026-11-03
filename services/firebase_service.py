"""Firebase Admin and Cloud Firestore Service.

Provides secure server-side management of:
- User profiles & Preferences
- Personal Digital Library (Saved books, reading status)
- Ratings & Reviews (CRUD, aggregated stats)
- Search History & Recommendation History
- Recently Viewed Books

Adheres strictly to private data ownership per user UID.
Gracefully handles missing credentials with clear diagnostic messages.
"""

import datetime
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Global singletons
_firebase_app = None
_firestore_db = None
_firebase_initialized = False
_initialization_error = None


def init_firebase(credentials_path: Optional[str] = None):
    """Initializes the Firebase Admin SDK if not already initialized."""
    global _firebase_app, _firestore_db, _firebase_initialized, _initialization_error

    if _firebase_initialized:
        return _firestore_db

    import firebase_admin
    from firebase_admin import credentials, firestore

    target_path = credentials_path or os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

    # Check if app is already initialized in firebase_admin registry
    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        _firestore_db = firestore.client()
        _firebase_initialized = True
        return _firestore_db

    # Check if credential file exists
    if os.path.exists(target_path):
        try:
            cred = credentials.Certificate(target_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            _firestore_db = firestore.client()
            _firebase_initialized = True
            logger.info("Firebase Admin SDK successfully initialized with %s", target_path)
            return _firestore_db
        except Exception as e:
            _initialization_error = str(e)
            logger.error("Failed to initialize Firebase Admin with credentials: %s", e)
            return None
    else:
        _initialization_error = (
            f"Firebase service account file '{target_path}' was not found. "
            "Please download your Firebase Service Account JSON from the Firebase Console "
            "and place it at the project root."
        )
        logger.warning(_initialization_error)
        return None


def get_firestore():
    """Returns the active Firestore client or None if not initialized."""
    global _firestore_db
    if _firestore_db is None:
        init_firebase()
    return _firestore_db


def is_firebase_ready() -> Tuple[bool, Optional[str]]:
    """Returns (True, None) if ready, or (False, reason) if not."""
    db = get_firestore()
    if db is not None:
        return True, None
    return False, _initialization_error


class FirebaseService:
    """Encapsulates all server-side Firestore operations with in-memory caching."""

    _user_cache_lock = threading.Lock()
    _user_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _USER_CACHE_TTL = 300  # 5 minutes TTL for user profiles

    # -------------------------------------------------------------------------
    # USER PROFILE & PREFERENCES
    # -------------------------------------------------------------------------

    @classmethod
    def get_or_create_user(cls, uid: str, email: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        """Ensures a user document exists in 'users' collection with snappy cached return."""
        # Check cache
        with cls._user_cache_lock:
            cached = cls._user_cache.get(uid)
            if cached and (time.time() - cached[0] < cls._USER_CACHE_TTL):
                return cached[1]

        default_data = {
            "uid": uid,
            "email": email,
            "fullName": full_name or email.split("@")[0].capitalize(),
            "createdAt": datetime.datetime.utcnow().isoformat(),
            "profileImage": f"https://api.dicebear.com/7.x/initials/svg?seed={full_name or email}",
            "favouriteCategories": ["Programming", "Technology", "Artificial Intelligence"],
        }

        db = get_firestore()
        if not db:
            with cls._user_cache_lock:
                cls._user_cache[uid] = (time.time(), default_data)
            return default_data

        try:
            doc_ref = db.collection("users").document(uid)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                with cls._user_cache_lock:
                    cls._user_cache[uid] = (time.time(), data)
                return data

            doc_ref.set(default_data)
            with cls._user_cache_lock:
                cls._user_cache[uid] = (time.time(), default_data)
            return default_data
        except Exception as e:
            logger.error("Firestore user sync error for %s: %s (serving fallback profile)", uid, e)
            with cls._user_cache_lock:
                cls._user_cache[uid] = (time.time(), default_data)
            return default_data

    @classmethod
    def get_user_profile(cls, uid: str) -> Optional[Dict[str, Any]]:
        # Check cache
        with cls._user_cache_lock:
            cached = cls._user_cache.get(uid)
            if cached and (time.time() - cached[0] < cls._USER_CACHE_TTL):
                return cached[1]

        db = get_firestore()
        if not db:
            return None
        try:
            doc = db.collection("users").document(uid).get()
            if doc.exists:
                data = doc.to_dict()
                with cls._user_cache_lock:
                    cls._user_cache[uid] = (time.time(), data)
                return data
            return None
        except Exception as e:
            logger.error("Error reading user profile %s: %s", uid, e)
            return None

    @classmethod
    def update_user_profile(cls, uid: str, update_data: Dict[str, Any]) -> bool:
        db = get_firestore()
        if not db:
            return False
        try:
            db.collection("users").document(uid).update(update_data)
            # Invalidate or update cache
            with cls._user_cache_lock:
                cached = cls._user_cache.get(uid)
                if cached:
                    updated = dict(cached[1])
                    updated.update(update_data)
                    cls._user_cache[uid] = (time.time(), updated)
            return True
        except Exception as e:
            logger.error("Error updating user %s: %s", uid, e)
            return False

    @classmethod
    def get_user_preferences(cls, uid: str) -> List[str]:
        """Gets user's favourite categories."""
        user = cls.get_user_profile(uid)
        if user and "favouriteCategories" in user:
            return user["favouriteCategories"]
        return ["Programming", "Technology"]

    @classmethod
    def save_user_preferences(cls, uid: str, categories: List[str]) -> bool:
        db = get_firestore()
        if not db:
            return False
        try:
            db.collection("users").document(uid).set(
                {"favouriteCategories": categories}, merge=True
            )
            # Also sync to dedicated user_preferences collection
            db.collection("user_preferences").document(uid).set({
                "uid": uid,
                "categories": categories,
                "updatedAt": datetime.datetime.utcnow().isoformat(),
            })
            # Update cache
            with cls._user_cache_lock:
                cached = cls._user_cache.get(uid)
                if cached:
                    updated = dict(cached[1])
                    updated["favouriteCategories"] = categories
                    cls._user_cache[uid] = (time.time(), updated)
            return True
        except Exception as e:
            logger.error("Error saving user preferences: %s", e)
            return False

    # -------------------------------------------------------------------------
    # USER LIBRARY (SAVED BOOKS & READING STATUS)
    # -------------------------------------------------------------------------

    @classmethod
    def add_to_library(
        cls,
        uid: str,
        google_book_id: str,
        book_data: Dict[str, Any],
        reading_status: str = "want_to_read",
    ) -> Dict[str, Any]:
        """Adds a book to user's personal library. Prevents duplicates."""
        db = get_firestore()
        if not db:
            return {"success": False, "message": "Firebase database not connected."}

        # Validate reading status
        valid_statuses = ("want_to_read", "currently_reading", "completed")
        if reading_status not in valid_statuses:
            reading_status = "want_to_read"

        # Unique document ID per user-book pair to prevent duplicates
        doc_id = f"{uid}_{google_book_id}"
        doc_ref = db.collection("user_library").document(doc_id)

        existing = doc_ref.get()
        existing_data = existing.to_dict() if existing.exists else {}
        now = datetime.datetime.utcnow().isoformat()

        # Parse page count
        page_count_raw = book_data.get("page_count")
        try:
            page_count = int(page_count_raw) if (page_count_raw and str(page_count_raw).isdigit()) else int(existing_data.get("pageCount", 200))
        except (ValueError, TypeError):
            page_count = int(existing_data.get("pageCount", 200))

        current_page = int(existing_data.get("currentPage", 0))
        progress_percent = min(100, max(0, int(round((current_page / max(1, page_count)) * 100))))

        entry = {
            "id": doc_id,
            "uid": uid,
            "googleBookId": google_book_id,
            "readingStatus": reading_status,
            "savedAt": existing_data.get("savedAt", now),
            "updatedAt": now,
            "bookTitle": book_data.get("title", "Untitled"),
            "bookAuthors": book_data.get("authors", ["Not available"]),
            "bookThumbnail": book_data.get("thumbnail", ""),
            "bookCategory": book_data.get("category", "General"),
            "bookRating": book_data.get("rating"),
            "pageCount": page_count,
            "currentPage": current_page,
            "progressPercent": progress_percent,
        }

        doc_ref.set(entry)
        action_word = "updated in" if existing.exists else "added to"
        return {
            "success": True,
            "message": f"Book successfully {action_word} your library!",
            "item": entry,
        }

    @classmethod
    def get_user_library(cls, uid: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches books saved in the user's personal digital library."""
        db = get_firestore()
        if not db:
            return []

        query = db.collection("user_library").where("uid", "==", uid)
        if status_filter and status_filter != "all":
            query = query.where("readingStatus", "==", status_filter)

        docs = query.stream()
        results = []
        for doc in docs:
            d = doc.to_dict()
            results.append(d)

        # Sort by most recently updated
        results.sort(key=lambda x: x.get("updatedAt", ""), reverse=True)
        return results

    @classmethod
    def update_reading_status(cls, uid: str, google_book_id: str, new_status: str) -> bool:
        db = get_firestore()
        if not db:
            return False

        doc_id = f"{uid}_{google_book_id}"
        doc_ref = db.collection("user_library").document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False

        # Security check: ensure book belongs to this user
        if doc.to_dict().get("uid") != uid:
            return False

        doc_ref.update({
            "readingStatus": new_status,
            "updatedAt": datetime.datetime.utcnow().isoformat(),
        })
        return True

    @classmethod
    def update_reading_progress(
        cls,
        uid: str,
        google_book_id: str,
        current_page: int,
        total_pages: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Updates reading progress page number, percent, and completion for a book."""
        db = get_firestore()
        if not db:
            return {"success": False, "message": "Database not connected."}

        doc_id = f"{uid}_{google_book_id}"
        doc_ref = db.collection("user_library").document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            return {"success": False, "message": "Book not found in your library."}

        existing = doc.to_dict()
        if existing.get("uid") != uid:
            return {"success": False, "message": "Unauthorized."}

        # Resolve page count
        page_count = total_pages or existing.get("pageCount") or 200
        try:
            page_count = max(1, int(page_count))
        except (ValueError, TypeError):
            page_count = 200

        current_page = max(0, int(current_page))
        progress_percent = min(100, max(0, int(round((current_page / page_count) * 100))))
        now = datetime.datetime.utcnow().isoformat()

        update_payload = {
            "currentPage": current_page,
            "pageCount": page_count,
            "progressPercent": progress_percent,
            "updatedAt": now,
        }

        # Automatically mark completed if reached final page
        status = existing.get("readingStatus", "currently_reading")
        if current_page >= page_count and status == "currently_reading":
            update_payload["readingStatus"] = "completed"
            status = "completed"

        doc_ref.update(update_payload)

        return {
            "success": True,
            "message": f"Reading progress saved: Completed Page {current_page} of {page_count} ({progress_percent}%)",
            "bookId": google_book_id,
            "currentPage": current_page,
            "pageCount": page_count,
            "progressPercent": progress_percent,
            "readingStatus": status,
        }

    @classmethod
    def remove_from_library(cls, uid: str, google_book_id: str) -> bool:
        """Removes a book from the user's library."""
        db = get_firestore()
        if not db:
            return False

        doc_id = f"{uid}_{google_book_id}"
        doc_ref = db.collection("user_library").document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            return False

        if doc.to_dict().get("uid") != uid:
            return False

        doc_ref.delete()
        return True

    @classmethod
    def get_library_statistics(cls, uid: str) -> Dict[str, int]:
        """Calculates total, reading, completed, and want to read counts for dashboard."""
        books = cls.get_user_library(uid)
        stats = {
            "total_saved": len(books),
            "currently_reading": sum(1 for b in books if b.get("readingStatus") == "currently_reading"),
            "completed": sum(1 for b in books if b.get("readingStatus") == "completed"),
            "want_to_read": sum(1 for b in books if b.get("readingStatus") == "want_to_read"),
        }
        return stats

    # -------------------------------------------------------------------------
    # RATINGS & REVIEWS
    # -------------------------------------------------------------------------

    @classmethod
    def add_or_update_review(
        cls,
        uid: str,
        user_name: str,
        user_email: str,
        google_book_id: str,
        rating: int,
        review_text: str,
    ) -> Dict[str, Any]:
        """Submit or update a book review and 1-5 star rating."""
        db = get_firestore()
        if not db:
            return {"success": False, "message": "Database not connected."}

        rating = max(1, min(int(rating), 5))
        review_text = review_text.strip()
        if not review_text:
            return {"success": False, "message": "Review text cannot be empty."}

        doc_id = f"{uid}_{google_book_id}"
        doc_ref = db.collection("reviews").document(doc_id)
        existing = doc_ref.get()
        now = datetime.datetime.utcnow().isoformat()

        review_data = {
            "id": doc_id,
            "uid": uid,
            "userName": user_name,
            "userEmail": user_email,
            "googleBookId": google_book_id,
            "rating": rating,
            "reviewText": review_text,
            "createdAt": existing.to_dict().get("createdAt") if existing.exists else now,
            "updatedAt": now,
        }

        doc_ref.set(review_data)
        return {"success": True, "message": "Your review has been saved!", "review": review_data}

    @classmethod
    def get_book_reviews(cls, google_book_id: str) -> Dict[str, Any]:
        """Fetches all reviews for a book and computes average rating."""
        db = get_firestore()
        if not db:
            return {"reviews": [], "average_rating": 0, "total_reviews": 0}

        docs = (
            db.collection("reviews")
            .where("googleBookId", "==", google_book_id)
            .stream()
        )
        reviews = [doc.to_dict() for doc in docs]
        reviews.sort(key=lambda r: r.get("updatedAt", ""), reverse=True)

        if reviews:
            avg_rating = round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 1)
        else:
            avg_rating = 0.0

        return {
            "reviews": reviews,
            "average_rating": avg_rating,
            "total_reviews": len(reviews),
        }

    @classmethod
    def delete_review(cls, uid: str, google_book_id: str) -> bool:
        """Deletes user's review with ownership verification."""
        db = get_firestore()
        if not db:
            return False

        doc_id = f"{uid}_{google_book_id}"
        doc_ref = db.collection("reviews").document(doc_id)
        doc = doc_ref.get()
        if not doc.exists or doc.to_dict().get("uid") != uid:
            return False

        doc_ref.delete()
        return True

    # -------------------------------------------------------------------------
    # SEARCH HISTORY & RECOMMENDATION HISTORY
    # -------------------------------------------------------------------------

    @classmethod
    def log_search(cls, uid: str, query: str):
        """Records a user search query."""
        db = get_firestore()
        if not db or not uid or not query.strip():
            return

        try:
            db.collection("search_history").add({
                "uid": uid,
                "searchQuery": query.strip(),
                "searchedAt": datetime.datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error("Failed to log search history: %s", e)

    @classmethod
    def get_user_search_history(cls, uid: str, limit: int = 15) -> List[Dict[str, Any]]:
        db = get_firestore()
        if not db:
            return []

        docs = db.collection("search_history").where("uid", "==", uid).stream()
        history = [d.to_dict() for d in docs]
        history.sort(key=lambda x: x.get("searchedAt", ""), reverse=True)
        return history[:limit]

    @classmethod
    def clear_search_history(cls, uid: str) -> bool:
        db = get_firestore()
        if not db:
            return False

        docs = db.collection("search_history").where("uid", "==", uid).stream()
        for doc in docs:
            doc.reference.delete()
        return True

    @classmethod
    def log_recommendation(cls, uid: str, query: str, recommended_book_ids: List[str]):
        """Logs an intelligent recommendation event."""
        db = get_firestore()
        if not db or not uid:
            return

        try:
            db.collection("recommendation_history").add({
                "uid": uid,
                "searchQuery": query,
                "recommendedBookIds": recommended_book_ids,
                "createdAt": datetime.datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error("Failed to log recommendation history: %s", e)

    @classmethod
    def get_recommendation_history(cls, uid: str, limit: int = 10) -> List[Dict[str, Any]]:
        db = get_firestore()
        if not db:
            return []

        docs = db.collection("recommendation_history").where("uid", "==", uid).stream()
        history = [d.to_dict() for d in docs]
        history.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return history[:limit]

    # -------------------------------------------------------------------------
    # RECENTLY VIEWED BOOKS
    # -------------------------------------------------------------------------

    @classmethod
    def log_book_view(cls, uid: str, book: Dict[str, Any]):
        db = get_firestore()
        if not db or not uid or not book.get("id"):
            return

        doc_id = f"{uid}_{book['id']}"
        try:
            db.collection("recently_viewed").document(doc_id).set({
                "uid": uid,
                "bookId": book["id"],
                "bookTitle": book.get("title", "Untitled"),
                "bookAuthors": book.get("authors", []),
                "bookThumbnail": book.get("thumbnail", ""),
                "bookCategory": book.get("category", "General"),
                "viewedAt": datetime.datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error("Failed to log recently viewed book: %s", e)

    @classmethod
    def get_recently_viewed(cls, uid: str, limit: int = 8) -> List[Dict[str, Any]]:
        db = get_firestore()
        if not db:
            return []

        docs = db.collection("recently_viewed").where("uid", "==", uid).stream()
        books = [d.to_dict() for d in docs]
        books.sort(key=lambda x: x.get("viewedAt", ""), reverse=True)
        return books[:limit]

