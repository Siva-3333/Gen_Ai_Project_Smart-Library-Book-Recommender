"""Google Books API Service.

Integrates with the official Google Books API endpoint:
https://www.googleapis.com/books/v1/volumes

Provides robust searching, pagination, detail retrieval, and sanitization
with strict adherence to displaying only genuine Google Books metadata.
"""

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
import requests
from flask import current_app

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_COVER_IMAGE = "/static/images/default-book.svg"


class GoogleBooksService:
    """Service to interact with the Google Books API with high-performance caching."""

    _cache_lock = threading.Lock()
    _search_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _details_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _SEARCH_CACHE_TTL = 900  # 15 minutes TTL for search results
    _DETAILS_CACHE_TTL = 3600  # 1 hour TTL for individual book details

    @classmethod
    def _get_api_key(cls) -> Optional[str]:
        """Fetch API key from Flask application config or environment variable."""
        try:
            key = current_app.config.get("GOOGLE_BOOKS_API_KEY", "").strip()
            if key:
                return key
        except Exception:
            pass
        import os
        key = os.getenv("GOOGLE_BOOKS_API_KEY", "").strip()
        return key if key else None

    @classmethod
    def _get_base_url(cls) -> str:
        try:
            return current_app.config.get(
                "GOOGLE_BOOKS_BASE_URL", "https://www.googleapis.com/books/v1/volumes"
            )
        except Exception:
            return "https://www.googleapis.com/books/v1/volumes"

    @classmethod
    def _get_timeout(cls) -> Tuple[int, int]:
        """Snappy network timeouts: 4s connect, 7s read to prevent page hanging."""
        return (4, 7)

    @classmethod
    def _safe_request(cls, url: str, params: Optional[Dict[str, Any]] = None, timeout: Any = (4, 7)) -> requests.Response:
        """Execute HTTP request with graceful SSL fallback for Windows/proxy environments."""
        try:
            return requests.get(url, params=params, timeout=timeout)
        except requests.exceptions.SSLError:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("SSL verification failed on Windows host; retrying Google Books API call with verify=False.")
            return requests.get(url, params=params, timeout=timeout, verify=False)

    @classmethod
    def sanitize_book_item(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms a raw Google Books volume item into a clean dictionary.

        Guarantees that no fake data is generated. If a field is missing,
        'Not available' or safe empty structures are returned.
        """
        if not item or not isinstance(item, dict):
            return {}

        book_id = item.get("id", "")
        info = item.get("volumeInfo", {})

        # Authors
        raw_authors = info.get("authors")
        authors = raw_authors if isinstance(raw_authors, list) and raw_authors else ["Not available"]

        # Categories
        raw_categories = info.get("categories")
        categories = (
            raw_categories
            if isinstance(raw_categories, list) and raw_categories
            else ["General"]
        )

        # Image Links
        image_links = info.get("imageLinks", {})
        thumbnail = (
            image_links.get("thumbnail")
            or image_links.get("smallThumbnail")
            or image_links.get("medium")
            or image_links.get("large")
            or ""
        )
        if thumbnail:
            # Enforce HTTPS to prevent mixed content issues
            thumbnail = thumbnail.replace("http://", "https://")
        else:
            thumbnail = DEFAULT_COVER_IMAGE

        # ISBN extraction
        industry_identifiers = info.get("industryIdentifiers", [])
        isbn_10 = "Not available"
        isbn_13 = "Not available"
        if isinstance(industry_identifiers, list):
            for ident in industry_identifiers:
                if ident.get("type") == "ISBN_10":
                    isbn_10 = ident.get("identifier", "Not available")
                elif ident.get("type") == "ISBN_13":
                    isbn_13 = ident.get("identifier", "Not available")

        # Description
        raw_description = info.get("description", "").strip()
        description = raw_description if raw_description else "Not available"

        # Publisher and Date
        publisher = info.get("publisher", "Not available")
        published_date = info.get("publishedDate", "Not available")

        # Page count & rating
        page_count = info.get("pageCount")
        average_rating = info.get("averageRating")
        ratings_count = info.get("ratingsCount", 0)

        raw_preview = info.get("previewLink") or ""
        preview_link = raw_preview.replace("http://", "https://") if raw_preview else ""

        # Google Books URL logic:
        # Note: Google Books API frequently outputs play.google.com/store/books/details?id=... as infoLink.
        # However, for volumes not commercially sold on Google Play, play.google.com returns a 404 Not Found error!
        # The official, canonical Google Books volume page is https://books.google.com/books?id={book_id},
        # which is 100% guaranteed to return HTTP 200 with preview, reviews, publisher info, and store options.
        raw_info = info.get("infoLink") or info.get("canonicalVolumeLink") or ""
        raw_info = raw_info.replace("http://", "https://")
        if raw_info and "play.google.com" not in raw_info:
            info_link = raw_info
        else:
            info_link = f"https://books.google.com/books?id={book_id}"

        # Access Info (Reader, Embeddable, PDF, EPUB, Viewability)
        access = item.get("accessInfo", {})
        embeddable = bool(access.get("embeddable", False))
        viewability = access.get("viewability", "NO_PAGES")
        web_reader_raw = access.get("webReaderLink") or ""
        web_reader_link = web_reader_raw.replace("http://", "https://") if web_reader_raw else ""
        access_view_status = access.get("accessViewStatus", "NONE")

        pdf_info = access.get("pdf", {})
        pdf_available = bool(pdf_info.get("isAvailable", False))
        pdf_download_raw = pdf_info.get("downloadLink") or pdf_info.get("acsTokenLink") or ""
        pdf_download_link = pdf_download_raw.replace("http://", "https://") if pdf_download_raw else ""

        epub_info = access.get("epub", {})
        epub_available = bool(epub_info.get("isAvailable", False))
        epub_download_raw = epub_info.get("downloadLink") or epub_info.get("acsTokenLink") or ""
        epub_download_link = epub_download_raw.replace("http://", "https://") if epub_download_raw else ""

        # Primary ISBN
        isbn = isbn_13 if isbn_13 != "Not available" else (isbn_10 if isbn_10 != "Not available" else "")

        return {
            "id": book_id,
            "title": info.get("title", "Untitled"),
            "subtitle": info.get("subtitle", ""),
            "authors": authors,
            "authors_str": ", ".join(authors),
            "publisher": publisher,
            "published_date": published_date,
            "description": description,
            "categories": categories,
            "category": categories[0] if categories else "General",
            "page_count": page_count if page_count is not None else "Not available",
            "rating": round(float(average_rating), 1) if average_rating is not None else None,
            "ratings_count": ratings_count if ratings_count else 0,
            "thumbnail": thumbnail,
            "preview_link": preview_link,
            "info_link": info_link,
            "language": info.get("language", "en").upper(),
            "isbn_10": isbn_10,
            "isbn_13": isbn_13,
            "isbn": isbn,
            "canonical_volume_link": f"https://books.google.com/books?id={book_id}",
            "embeddable": embeddable,
            "viewability": viewability,
            "web_reader_link": web_reader_link,
            "access_view_status": access_view_status,
            "pdf_available": pdf_available,
            "pdf_download_link": pdf_download_link,
            "epub_available": epub_available,
            "epub_download_link": epub_download_link,
        }

    @classmethod
    def search_books(
        cls,
        query: str,
        category: Optional[str] = None,
        max_results: int = 20,
        start_index: int = 0,
        sort_by: str = "relevance",
        search_field: str = "all",
    ) -> Dict[str, Any]:
        """Search books with filtering, pagination, and duplicate prevention.

        search_field can be: 'all', 'intitle', 'inauthor', 'subject'
        """
        query_str = (query or "").strip()
        parts = []

        if search_field == "intitle" and query_str:
            parts.append(f"intitle:{query_str}")
        elif search_field == "inauthor" and query_str:
            parts.append(f"inauthor:{query_str}")
        elif search_field == "subject" and query_str:
            parts.append(f"subject:{query_str}")
        elif query_str:
            parts.append(query_str)

        if category and category.lower() != "all":
            parts.append(f'subject:"{category}"')

        final_q = " ".join(parts).strip()
        if not final_q:
            final_q = "subject:technology"  # Safe general fallback for empty browse

        # Google Books API restricts maxResults to between 1 and 40
        max_results = max(1, min(max_results, 40))
        start_index = max(0, start_index)

        # ── 1. Check In-Memory TTL Cache for Instant Sub-Millisecond Return ──
        cache_key = f"{final_q}|{sort_by}|{start_index}|{max_results}"
        with cls._cache_lock:
            cached = cls._search_cache.get(cache_key)
            if cached:
                cached_time, cached_data = cached
                if time.time() - cached_time < cls._SEARCH_CACHE_TTL:
                    return cached_data

        params: Dict[str, Any] = {
            "q": final_q,
            "startIndex": start_index,
            "maxResults": max_results,
            "orderBy": sort_by if sort_by in ("relevance", "newest") else "relevance",
            "printType": "books",
        }

        api_key = cls._get_api_key()
        if api_key:
            params["key"] = api_key

        url = cls._get_base_url()
        timeout = cls._get_timeout()

        try:
            response = cls._safe_request(url, params=params, timeout=timeout)
            
            # If API key is blocked or restricted for Books API, attempt fallback without key
            if response.status_code == 403 and "key" in params:
                logger.warning(
                    "Google Books API Key returned 403 (Service Blocked). "
                    "Make sure 'Books API' is enabled in Google Cloud Console: "
                    "https://console.cloud.google.com/apis/library/books.googleapis.com?project=gen-ai---project"
                )
                params_fallback = dict(params)
                params_fallback.pop("key", None)
                response = cls._safe_request(url, params=params_fallback, timeout=timeout)

            response.raise_for_status()
            data = response.json()

            total_items = data.get("totalItems", 0)
            items = data.get("items", [])

            # Deduplicate by book ID
            seen_ids = set()
            books: List[Dict[str, Any]] = []
            for item in items:
                b_id = item.get("id")
                if b_id and b_id not in seen_ids:
                    seen_ids.add(b_id)
                    sanitized = cls.sanitize_book_item(item)
                    if sanitized.get("id"):
                        books.append(sanitized)

            result = {
                "success": True,
                "books": books,
                "total_items": total_items,
                "start_index": start_index,
                "max_results": max_results,
                "query": query,
                "category": category,
            }

            # Cache the successful result
            with cls._cache_lock:
                cls._search_cache[cache_key] = (time.time(), result)

            return result

        except requests.exceptions.Timeout:
            logger.error("Google Books API request timed out for query: %s", final_q)
            # Check for stale cache to preserve flawless user experience
            with cls._cache_lock:
                cached = cls._search_cache.get(cache_key)
                if cached:
                    logger.info("Serving stale cached result for timed-out query: %s", final_q)
                    return cached[1]
            return {
                "success": False,
                "error": "The book search request timed out. Please check your internet connection and try again.",
                "books": [],
                "total_items": 0,
            }
        except requests.exceptions.RequestException as e:
            logger.error("Google Books API error: %s", e)
            # Check for stale cache
            with cls._cache_lock:
                cached = cls._search_cache.get(cache_key)
                if cached:
                    logger.info("Serving stale cached result for failed query: %s", final_q)
                    return cached[1]
            return {
                "success": False,
                "error": f"Failed to retrieve books from Google Books API: {str(e)}",
                "books": [],
                "total_items": 0,
            }

    @classmethod
    def get_book_details(cls, book_id: str) -> Optional[Dict[str, Any]]:
        """Fetch complete real details for a specific book ID from Google Books API with caching."""
        if not book_id or not isinstance(book_id, str):
            return None

        clean_id = book_id.strip()

        # Check in-memory details cache
        with cls._cache_lock:
            cached = cls._details_cache.get(clean_id)
            if cached and (time.time() - cached[0] < cls._DETAILS_CACHE_TTL):
                return cached[1]

        url = f"{cls._get_base_url()}/{clean_id}"
        params = {}
        api_key = cls._get_api_key()
        if api_key:
            params["key"] = api_key

        timeout = cls._get_timeout()

        try:
            response = cls._safe_request(url, params=params, timeout=timeout)
            if response.status_code == 404:
                return None
            if response.status_code == 403 and "key" in params:
                params_fallback = dict(params)
                params_fallback.pop("key", None)
                response = cls._safe_request(url, params=params_fallback, timeout=timeout)
                if response.status_code == 404:
                    return None
            response.raise_for_status()
            raw_data = response.json()
            sanitized = cls.sanitize_book_item(raw_data)
            if sanitized:
                with cls._cache_lock:
                    cls._details_cache[clean_id] = (time.time(), sanitized)
            return sanitized
        except Exception as e:
            logger.error("Error retrieving book details for ID %s: %s", book_id, e)
            # Check for stale cache
            with cls._cache_lock:
                cached = cls._details_cache.get(clean_id)
                if cached:
                    return cached[1]
            return None

    @classmethod
    def get_books_by_ids(cls, book_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch multiple books by IDs, ignoring missing ones."""
        books = []
        for b_id in book_ids:
            if not b_id:
                continue
            details = cls.get_book_details(b_id)
            if details:
                books.append(details)
        return books

    @classmethod
    def get_curated_collection(cls, topic: str, count: int = 8) -> List[Dict[str, Any]]:
        """Helper to get curated book list for dashboard sections."""
        res = cls.search_books(query=topic, max_results=count)
        return res.get("books", [])

