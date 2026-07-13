import logging
from flask import Blueprint, request, jsonify

contact_bp = Blueprint("contact", __name__)

logger = logging.getLogger(__name__)


@contact_bp.route("/contact", methods=["POST"])
def submit_contact():
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400

    name = (data.get("name") or "").strip()
    message = (data.get("message") or "").strip()

    if not name or not message:
        return jsonify({"error": "نام و پیام الزامی است"}), 400

    if len(name) > 120:
        return jsonify({"error": "نام بیش از حد طولانی است"}), 400

    if len(message) > 2000:
        return jsonify({"error": "پیام بیش از حد طولانی است"}), 400

    logger.info(
        "Contact form submission: name=%s, phone=%s, message=%s",
        name, data.get("phone", ""), message[:100],
    )

    return jsonify({"message": "پیام شما با موفقیت دریافت شد"}), 201
