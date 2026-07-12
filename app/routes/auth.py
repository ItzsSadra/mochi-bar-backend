from datetime import timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "نام کاربری و رمز عبور الزامی است"}), 400

    user = User.query.filter_by(username=data["username"]).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "نام کاربری یا رمز عبور اشتباه است"}), 401

    if not user.is_active:
        return jsonify({"error": "حساب کاربری غیرفعال است"}), 403

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
