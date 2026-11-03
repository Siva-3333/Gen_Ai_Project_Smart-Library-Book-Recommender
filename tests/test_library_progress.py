"""Unit tests for reading progress tracking, increment actions, and status updates."""

import unittest
from unittest.mock import MagicMock, patch
from app import create_app
from services.firebase_service import FirebaseService


class TestReadingProgress(unittest.TestCase):
    """Test suite verifying reading progress updates, page increments, and completion."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True

    def setUp(self):
        self.client = self.app.test_client()

    def test_progress_unauthenticated(self):
        """Unauthenticated requests to /api/library/progress must return 401."""
        res = self.client.post("/api/library/progress", json={"bookId": "test123", "action": "increment"})
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data.get("success", True))

    @patch("services.firebase_service.FirebaseService.get_user_library")
    @patch("services.firebase_service.FirebaseService.update_reading_progress")
    def test_progress_increment_existing_book(self, mock_update, mock_get_lib):
        """Authenticated user incrementing progress on an existing book from page 7 to 8."""
        mock_get_lib.return_value = [
            {
                "googleBookId": "book_abc",
                "bookTitle": "Clean Code",
                "currentPage": 7,
                "pageCount": 464,
                "readingStatus": "currently_reading",
            }
        ]
        mock_update.return_value = {
            "success": True,
            "bookId": "book_abc",
            "currentPage": 8,
            "pageCount": 464,
            "progressPercent": 2,
            "readingStatus": "currently_reading",
        }

        with self.client.session_transaction() as sess:
            sess["user"] = {"uid": "user_mock_123", "name": "Reader"}

        res = self.client.post(
            "/api/library/progress",
            json={"bookId": "book_abc", "action": "increment"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["currentPage"], 8)
        self.assertEqual(data["readingStatus"], "currently_reading")
        mock_update.assert_called_once_with(
            uid="user_mock_123",
            google_book_id="book_abc",
            current_page=8,
            total_pages=464,
        )

    @patch("services.firebase_service.FirebaseService.update_reading_progress")
    def test_progress_set_page_success(self, mock_update):
        """Authenticated user setting specific page number (e.g. Page 150 of 300)."""
        mock_update.return_value = {
            "success": True,
            "bookId": "book_xyz",
            "currentPage": 150,
            "pageCount": 300,
            "progressPercent": 50,
            "readingStatus": "currently_reading",
        }

        with self.client.session_transaction() as sess:
            sess["user"] = {"uid": "user_mock_123", "name": "Reader"}

        res = self.client.post(
            "/api/library/progress",
            json={"bookId": "book_xyz", "action": "set", "currentPage": 150, "totalPages": 300},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["currentPage"], 150)
        self.assertEqual(data["progressPercent"], 50)
        mock_update.assert_called_once_with(
            uid="user_mock_123",
            google_book_id="book_xyz",
            current_page=150,
            total_pages=300,
        )

    @patch("services.firebase_service.FirebaseService.update_reading_progress")
    def test_progress_completes_when_last_page_reached(self, mock_update):
        """When reaching the last page, status transitions to completed."""
        mock_update.return_value = {
            "success": True,
            "bookId": "book_done",
            "currentPage": 250,
            "pageCount": 250,
            "progressPercent": 100,
            "readingStatus": "completed",
        }

        with self.client.session_transaction() as sess:
            sess["user"] = {"uid": "user_mock_123", "name": "Reader"}

        res = self.client.post(
            "/api/library/progress",
            json={"bookId": "book_done", "action": "set", "currentPage": 250, "totalPages": 250},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["readingStatus"], "completed")
        self.assertEqual(data["progressPercent"], 100)


if __name__ == "__main__":
    unittest.main()
