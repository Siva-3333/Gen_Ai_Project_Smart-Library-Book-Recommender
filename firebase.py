import os
import firebase_admin
from firebase_admin import credentials, firestore

_db = None


def get_db():
    """Returns the Firestore client, initialising Firebase on first call."""
    global _db
    if _db is None:
        cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase-adminsdk.json")
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db

