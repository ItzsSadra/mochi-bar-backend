from datetime import timedelta, datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)

# Simple in-memory rate limiter
_login_attempts: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 300  # 5 minutes
RATE_LIMIT_MAX = 10     # max attempts per window


def _check_rate_limit(ip: str) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    cutoff = now - RATE_LIMIT_WINDOW
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if t > cutoff]
    _login_attempts[ip] = attempts
    return len(attempts) < RATE_LIMIT_MAX


def _record_login_attempt(ip: str) -> None:
    now = datetime.now(timezone.utc).timestamp()
    _login_attempts.setdefault(ip, []).append(now)


@auth_bp.route("/login", methods=["POST"])
def login():
    ip = request.remote_addr or "unknown"
    if not _check_rate_limit(ip):
        return jsonify({"error": "تعداد تلاش‌ها بیش از حد مجاز است. لطفاً چند دقیقه صبر کنید"}), 429

    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "نام کاربری و رمز عبور الزامی است"}), 400

    user = User.query.filter_by(username=data["username"]).first()
    if not user or not user.check_password(data["password"]):
        _record_login_attempt(ip)
        return jsonify({"error": "نام کاربری یا رمز عبور اشتباه است"}), 401

    if not user.is_active:
        return jsonify({"error": "حساب کاربری غیرفعال است"}), 403

    _login_attempts.pop(ip, None)
    access_token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(hours=24),
    )
    return jsonify({
        "token": access_token,
        "user": user.to_dict(),
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "توکن نامعتبر است"}), 401
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "کاربر یافت نشد"}), 404
    return jsonify({"user": user.to_dict()})


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "توکن نامعتبر است"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "کاربر یافت نشد"}), 404

    data = request.get_json()
    if not data or not data.get("current_password") or not data.get("new_password"):
        return jsonify({"error": "رمز عبور فعلی و جدید الزامی است"}), 400

    new_password = data["new_password"]
    if len(new_password) < 8:
        return jsonify({"error": "رمز عبور جدید باید حداقل ۸ کاراکتر باشد"}), 400

    if not user.check_password(data["current_password"]):
        return jsonify({"error": "رمز عبور فعلی اشتباه است"}), 401

    user.set_password(new_password)
    db.session.commit()
    return jsonify({"message": "رمز عبور با موفقیت تغییر کرد"})
