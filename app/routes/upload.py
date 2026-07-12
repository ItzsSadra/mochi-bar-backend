import uuid
import logging
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app.models import db
from app.models.media import Media
from app.supabase import upload_to_storage

logger = logging.getLogger(__name__)

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _safe_folder(folder):
    folder = secure_filename(folder)
    if not folder or folder.startswith("."):
        folder = "default"
    return folder


@upload_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "فایلی ارسال نشد"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "فایلی انتخاب نشد"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "فرمت فایل پشتیبانی نمی‌شود"}), 400

    folder = _safe_folder(request.form.get("folder", "default"))
    original_name = secure_filename(file.filename)
    ext = original_name.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_data = file.read()
    file_size = len(file_data)
    content_type = file.content_type or f"image/{ext}"

    try:
        public_url = upload_to_storage(folder, filename, file_data, content_type)
    except Exception:
        logger.exception("Supabase upload failed")
        return jsonify({"error": "خطا در آپلود فایل"}), 500

    media = Media(
        filename=filename,
        original_name=original_name,
        file_path=public_url,
        file_size=file_size,
        mime_type=content_type,
        folder=folder,
        alt_text=request.form.get("alt_text"),
    )
    db.session.add(media)
    db.session.commit()

    return jsonify({
        "media": media.to_dict(),
        "url": public_url,
    }), 201


@upload_bp.route("/upload/multiple", methods=["POST"])
@jwt_required()
def upload_multiple():
    if "files" not in request.files:
        return jsonify({"error": "فایلی ارسال نشد"}), 400

    files = request.files.getlist("files")
    folder = _safe_folder(request.form.get("folder", "default"))
    uploaded = []

    for file in files:
        if file.filename == "" or not allowed_file(file.filename):
            continue

        original_name = secure_filename(file.filename)
        ext = original_name.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file_data = file.read()
        file_size = len(file_data)
        content_type = file.content_type or f"image/{ext}"

        try:
            public_url = upload_to_storage(folder, filename, file_data, content_type)
        except Exception:
            logger.exception("Supabase upload failed for %s", original_name)
            continue

        media = Media(
            filename=filename,
            original_name=original_name,
            file_path=public_url,
            file_size=file_size,
            mime_type=content_type,
            folder=folder,
        )
        db.session.add(media)
        uploaded.append(media)

    db.session.commit()

    return jsonify({
        "files": [m.to_dict() for m in uploaded],
        "count": len(uploaded),
    }), 201


@upload_bp.route("/uploads/<folder>/<filename>", methods=["GET"])
def serve_upload(folder, filename):
    from app.supabase import extract_storage_path, get_supabase, BUCKET
    from flask import redirect

    folder = _safe_folder(folder)
    filename = secure_filename(filename)

    supabase_url = current_app.config.get("SUPABASE_URL")
    if supabase_url:
        path = f"{folder}/{filename}"
        try:
            public_url = get_supabase().storage.from_(BUCKET).get_public_url(path)
            return redirect(public_url, code=302)
        except Exception:
            pass

    import os
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], folder)
    return send_from_directory(upload_dir, filename)
