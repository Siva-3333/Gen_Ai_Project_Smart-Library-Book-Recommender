"""Authentication Routes and Session Management.

Handles split-screen Login, Registration, Password Reset trigger,
and synchronizes Firebase client-side authentication tokens with Flask sessions.
"""

from functools import wraps
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from services.firebase_service import FirebaseService

auth_bp = Blueprint("auth", __name__)


def login_required(f):
    """Decorator to enforce authenticated session for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session or not session["user"].get("uid"):
            if request.path.startswith("/api/") or request.is_json:
                return jsonify({"success": False, "message": "Authentication required. Please log in."}), 401
            # Redirect to login with return path
            return redirect(url_for("auth.login_page", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/login")
def login_page():
    if "user" in session and session["user"].get("uid"):
        return redirect(url_for("profile.dashboard_page"))
    return render_template("login.html")


@auth_bp.route("/register")
def register_page():
    if "user" in session and session["user"].get("uid"):
        return redirect(url_for("profile.dashboard_page"))
    return render_template("register.html")


@auth_bp.route("/logout")
def logout_page():
    session.clear()
    return redirect(url_for("auth.login_page"))


@auth_bp.route("/api/auth/session-login", methods=["POST"])
def session_login():
    """Syncs Firebase authenticated client state with Flask session."""
    data = request.get_json(silent=True) or {}
    uid = data.get("uid")
    email = data.get("email")
    display_name = data.get("displayName") or (email.split("@")[0].capitalize() if email else "Reader")
    favourite_categories = data.get("favouriteCategories")

    if not uid or not email:
        return jsonify({"success": False, "message": "UID and Email are required"}), 400

    # Ensure user document is in Firestore
    user_doc = FirebaseService.get_or_create_user(uid=uid, email=email, full_name=display_name)

    # If preferences were passed during registration, save them
    if favourite_categories and isinstance(favourite_categories, list):
        FirebaseService.save_user_preferences(uid, favourite_categories)
        user_doc["favouriteCategories"] = favourite_categories

    # Store user in Flask session
    session["user"] = {
        "uid": uid,
        "email": email,
        "displayName": user_doc.get("fullName", display_name),
        "profileImage": user_doc.get("profileImage", ""),
        "favouriteCategories": user_doc.get("favouriteCategories", []),
    }
    session.permanent = True

    return jsonify({
        "success": True,
        "message": "Session established successfully",
        "user": session["user"],
    })


@auth_bp.route("/api/auth/session-logout", methods=["POST"])
def session_logout():
    session.clear()
    return jsonify({"success": True, "message": "Session terminated"})


@auth_bp.route("/api/auth/current-user")
def current_user():
    user = session.get("user")
    if user:
        return jsonify({"authenticated": True, "user": user})
    return jsonify({"authenticated": False, "user": None})

