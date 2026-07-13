import os
import logging
from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import JWTManager
from app.config import Config
from app.models import db

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    raw = os.getenv("CORS_ORIGINS", "").strip()
    allowed_origins = [o.strip() for o in raw.split(",") if o.strip()] if raw else ["*"]

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin", "*")
        if "*" in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = allowed_origins[0] if allowed_origins else "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = make_response()
            response.status_code = 204
            return response

    db.init_app(app)
    JWTManager(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "یافت نشد"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "روش مجاز نیست"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return jsonify({"error": "خطای داخلی سرور"}), 500

    from app.routes.auth import auth_bp
    from app.routes.menu import menu_bp
    from app.routes.categories import categories_bp
    from app.routes.gallery import gallery_bp
    from app.routes.settings import settings_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.upload import upload_bp
    from app.routes.media import media_bp
    from app.routes.contact import contact_bp
    from app.routes.health import health_bp

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(menu_bp, url_prefix="/api")
    app.register_blueprint(categories_bp, url_prefix="/api")
    app.register_blueprint(gallery_bp, url_prefix="/api")
    app.register_blueprint(settings_bp, url_prefix="/api")
    app.register_blueprint(dashboard_bp, url_prefix="/api")
    app.register_blueprint(upload_bp, url_prefix="/api")
    app.register_blueprint(media_bp, url_prefix="/api")
    app.register_blueprint(contact_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix="/api")

    return app
