from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db
from app.models.setting import Setting

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET"])
def get_settings():
    settings = Setting.query.all()
    result = {}
    for s in settings:
        if s.group not in result:
            result[s.group] = {}
        result[s.group][s.key] = s.value
    return jsonify({"settings": result})


@settings_bp.route("/settings", methods=["PUT"])
@jwt_required()
def update_settings():
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400

    for key, value in data.items():
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = Setting(key=key, value=str(value))
            db.session.add(setting)

    db.session.commit()
    return jsonify({"message": "تنظیمات با موفقیت ذخیره شد"})


@settings_bp.route("/settings/<key>", methods=["GET"])
def get_setting(key):
    setting = Setting.query.filter_by(key=key).first()
    if not setting:
        return jsonify({"error": "تنظیم یافت نشد"}), 404
    return jsonify({"setting": setting.to_dict()})


@settings_bp.route("/settings/<key>", methods=["PUT"])
@jwt_required()
def update_setting(key):
    data = request.get_json()
    if not data or "value" not in data:
        return jsonify({"error": "مقدار الزامی است"}), 400

    setting = Setting.query.filter_by(key=key).first()
    if setting:
        setting.value = str(data["value"])
    else:
        setting = Setting(key=key, value=str(data["value"]), group=data.get("group", "general"))
        db.session.add(setting)

    db.session.commit()
    return jsonify({"setting": setting.to_dict()})
