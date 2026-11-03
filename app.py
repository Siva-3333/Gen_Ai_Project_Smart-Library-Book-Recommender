"""Smart Library Book Recommender - Main Flask Application.

Full-stack production-grade architecture combining:
- Flask Backend with Blueprint routing
- Google Books API Integration
- Python-based NLP & TF-IDF Cosine Similarity Recommendation Engine
- Firebase Authentication & Cloud Firestore Database
"""

import logging
from flask import Flask, render_template, session
from config import Config
from services.firebase_service import init_firebase, is_firebase_ready

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smart_library")


def create_app(config_class=Config):
    """Application factory for Smart Library."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Firebase Admin SDK
    init_firebase(app.config.get("FIREBASE_CREDENTIALS_PATH"))

    # Register Blueprints
    from routes.auth_routes import auth_bp
    from routes.book_routes import book_bp
    from routes.recommendation_routes import rec_bp
    from routes.library_routes import library_bp
    from routes.review_routes import review_bp
    from routes.history_routes import history_bp
    from routes.profile_routes import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(book_bp)
    app.register_blueprint(rec_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(profile_bp)

    # Context Processors (Injected into every Jinja2 template)
    @app.context_processor
    def inject_global_data():
        ready, reason = is_firebase_ready()
        return {
            "current_user": session.get("user"),
            "all_categories": app.config.get("CATEGORIES", []),
            "firebase_client_config": app.config.get("FIREBASE_CLIENT_CONFIG", {}),
            "firebase_ready": ready,
            "firebase_notice": reason,
        }

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html", message="The requested page could not be found."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("404.html", message="An unexpected server error occurred. Please try again."), 500

    return app


app = create_app()

if __name__ == "__main__":
    logger.info("Starting Smart Library Book Recommender on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)

