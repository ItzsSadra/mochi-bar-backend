from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db
from app.models.gallery import GalleryImage

gallery_bp = Blueprint("gallery", __name__)


@gallery_bp.route("/gallery", methods=["GET"])
def get_gallery():
    images = GalleryImage.query.filter_by(is_active=True).order_by(
        GalleryImage.sort_order, GalleryImage.id.desc()
    ).all()
    return jsonify({"images": [img.to_dict() for img in images]})


@gallery_bp.route("/gallery/<int:image_id>", methods=["GET"])
def get_gallery_image(image_id):
    image = GalleryImage.query.filter_by(id=image_id, is_active=True).first_or_404()
    return jsonify({"image": image.to_dict()})


@gallery_bp.route("/gallery", methods=["POST"])
@jwt_required()
def create_gallery_image():
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400
    if not data.get("image_url"):
        return jsonify({"error": "آدرس تصویر الزامی است"}), 400

    max_order = db.session.query(db.func.max(GalleryImage.sort_order)).scalar() or 0

    image = GalleryImage(
        title=data.get("title"),
        caption=data.get("caption"),
        image_url=data["image_url"],
        sort_order=data.get("sort_order", max_order + 1),
        is_active=data.get("is_active", True),
    )
    db.session.add(image)
    db.session.commit()
    return jsonify({"image": image.to_dict()}), 201


@gallery_bp.route("/gallery/<int:image_id>", methods=["PUT"])
@jwt_required()
def update_gallery_image(image_id):
    image = GalleryImage.query.get_or_404(image_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400

    if "title" in data:
        image.title = data["title"]
    if "caption" in data:
        image.caption = data["caption"]
    if "image_url" in data:
        image.image_url = data["image_url"]
    if "sort_order" in data:
        image.sort_order = data["sort_order"]
    if "is_active" in data:
        image.is_active = data["is_active"]

    db.session.commit()
    return jsonify({"image": image.to_dict()})


@gallery_bp.route("/gallery/<int:image_id>", methods=["DELETE"])
@jwt_required()
def delete_gallery_image(image_id):
    image = GalleryImage.query.get_or_404(image_id)
    db.session.delete(image)
    db.session.commit()
    return jsonify({"message": "تصویر گالری حذف شد"})
