import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db
from app.models.media import Media
from app.supabase import extract_storage_path, delete_from_storage

logger = logging.getLogger(__name__)

media_bp = Blueprint("media", __name__)


@media_bp.route("/media", methods=["GET"])
@jwt_required()
def get_media():
    folder = request.args.get("folder")
    search = request.args.get("search")

    query = Media.query

    if folder:
        query = query.filter_by(folder=folder)
    if search:
        query = query.filter(
            db.or_(
                Media.original_name.ilike(f"%{search}%"),
                Media.alt_text.ilike(f"%{search}%"),
            )
        )

    media = query.order_by(Media.id.desc()).all()
    return jsonify({"media": [m.to_dict() for m in media]})


@media_bp.route("/media/<int:media_id>", methods=["PUT"])
@jwt_required()
def update_media(media_id):
    media = Media.query.get_or_404(media_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400

    if "alt_text" in data:
        media.alt_text = data["alt_text"]
    if "folder" in data:
        media.folder = data["folder"]

    db.session.commit()
    return jsonify({"media": media.to_dict()})


@media_bp.route("/media/<int:media_id>", methods=["DELETE"])
@jwt_required()
def delete_media(media_id):
    media = Media.query.get_or_404(media_id)

    storage_path = extract_storage_path(media.file_path)
    if storage_path:
        delete_from_storage(storage_path)
    else:
        logger.debug("Media %s has no Supabase path, skipping storage delete", media_id)

    db.session.delete(media)
    db.session.commit()
    return jsonify({"message": "فایل حذف شد"})


@media_bp.route("/media/folders", methods=["GET"])
@jwt_required()
def get_folders():
    folders = db.session.query(Media.folder).distinct().all()
    return jsonify({"folders": [f[0] for f in folders]})
