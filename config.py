import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "smart-library-dev-secret-key-2026")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    # Google Books API
    GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "").strip()
    GOOGLE_BOOKS_BASE_URL = "https://www.googleapis.com/books/v1/volumes"
    DEFAULT_TIMEOUT = 12  # seconds

    # Firebase Admin SDK credentials path
    FIREBASE_CREDENTIALS_PATH = os.getenv(
        "FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json"
    )

    # Firebase Client Config (Safe for frontend exposure, used by Firebase Auth JS SDK)
    FIREBASE_CLIENT_CONFIG = {
        "apiKey": os.getenv("FIREBASE_API_KEY", ""),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.getenv("FIREBASE_APP_ID", ""),
    }

    # Available Curated Categories
    CATEGORIES = [
        "Programming",
        "Artificial Intelligence",
        "Machine Learning",
        "Data Science",
        "Science",
        "Technology",
        "Fiction",
        "Mystery",
        "Thriller",
        "History",
        "Business",
        "Self-help",
        "Biography",
        "Education",
    ]

    # AI / LLM Configuration (Optional Open-Source Ollama)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

    # Session configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
