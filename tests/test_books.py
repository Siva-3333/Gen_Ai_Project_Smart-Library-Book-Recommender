"""Unit tests for Google Books service and volume sanitization."""

import unittest
from services.google_books_service import GoogleBooksService, DEFAULT_COVER_IMAGE


class TestGoogleBooksService(unittest.TestCase):
    """Test suite verifying Google Books API parsing and sanitization."""

    def test_sanitize_complete_volume(self):
        sample_item = {
            "id": "test_id_101",
            "volumeInfo": {
                "title": "Learning Python",
                "subtitle": "Powerful Object-Oriented Programming",
                "authors": ["Mark Lutz"],
                "publisher": "O'Reilly Media",
                "publishedDate": "2013-06-12",
                "description": "Get a comprehensive, in-depth introduction to the core Python language.",
                "pageCount": 1600,
                "categories": ["Computers", "Programming"],
                "averageRating": 4.5,
                "ratingsCount": 240,
                "imageLinks": {
                    "thumbnail": "http://books.google.com/books/content?id=test&printsec=frontcover&img=1"
                },
                "language": "en",
                "industryIdentifiers": [
                    {"type": "ISBN_10", "identifier": "1449355730"},
                    {"type": "ISBN_13", "identifier": "9781449355739"},
                ],
                "infoLink": "https://books.google.com/books?id=test_id_101",
            },
        }

        sanitized = GoogleBooksService.sanitize_book_item(sample_item)

        self.assertEqual(sanitized["id"], "test_id_101")
        self.assertEqual(sanitized["title"], "Learning Python")
        self.assertEqual(sanitized["authors"], ["Mark Lutz"])
        self.assertEqual(sanitized["authors_str"], "Mark Lutz")
        self.assertEqual(sanitized["publisher"], "O'Reilly Media")
        self.assertEqual(sanitized["published_date"], "2013-06-12")
        self.assertEqual(sanitized["page_count"], 1600)
        self.assertEqual(sanitized["rating"], 4.5)
        self.assertEqual(sanitized["ratings_count"], 240)
        self.assertEqual(sanitized["isbn_10"], "1449355730")
        self.assertEqual(sanitized["isbn_13"], "9781449355739")
        # Ensure HTTPS replacement
        self.assertTrue(sanitized["thumbnail"].startswith("https://"))

    def test_sanitize_missing_metadata_handled_gracefully(self):
        sparse_item = {
            "id": "sparse_999",
            "volumeInfo": {
                # Title, authors, description, images missing
            },
        }

        sanitized = GoogleBooksService.sanitize_book_item(sparse_item)

        self.assertEqual(sanitized["id"], "sparse_999")
        self.assertEqual(sanitized["title"], "Untitled")
        self.assertEqual(sanitized["authors"], ["Not available"])
        self.assertEqual(sanitized["publisher"], "Not available")
        self.assertEqual(sanitized["description"], "Not available")
        self.assertEqual(sanitized["page_count"], "Not available")
        self.assertIsNone(sanitized["rating"])
        self.assertEqual(sanitized["thumbnail"], DEFAULT_COVER_IMAGE)


if __name__ == "__main__":
    unittest.main()

