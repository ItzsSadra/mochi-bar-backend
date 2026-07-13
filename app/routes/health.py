from flask import Blueprint, jsonify
from app.models import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "ok", "database": "connected"})
    except Exception:
        return jsonify({"status": "degraded", "database": "disconnected"}), 503
