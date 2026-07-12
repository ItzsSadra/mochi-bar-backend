from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db
from app.models.category import Category

categories_bp = Blueprint("categories", __name__)


@categories_bp.route("/categories", methods=["GET"])
def get_categories():
    categories = Category.query.order_by(Category.sort_order, Category.id).all()
    return jsonify({"categories": [cat.to_dict() for cat in categories]})


@categories_bp.route("/categories/<int:cat_id>", methods=["GET"])
def get_category(cat_id):
    category = Category.query.get_or_404(cat_id)
    return jsonify({"category": category.to_dict()})


@categories_bp.route("/categories", methods=["POST"])
@jwt_required()
def create_category():
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400
    if not data.get("name"):
        return jsonify({"error": "نام دسته‌بندی الزامی است"}), 400

    slug = data.get("slug") or data["name"].replace(" ", "-")

    existing = Category.query.filter_by(slug=slug).first()
    if existing:
        return jsonify({"error": "این دسته‌بندی قبلاً ایجاد شده است"}), 400

    category = Category(
        name=data["name"],
        slug=slug,
        description=data.get("description", ""),
        icon=data.get("icon"),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
    )
    db.session.add(category)
    db.session.commit()
    return jsonify({"category": category.to_dict()}), 201


@categories_bp.route("/categories/<int:cat_id>", methods=["PUT"])
@jwt_required()
def update_category(cat_id):
    category = Category.query.get_or_404(cat_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400

    if "slug" in data:
        existing = Category.query.filter(
            Category.slug == data["slug"],
            Category.id != cat_id,
        ).first()
        if existing:
            return jsonify({"error": "این نامک قبلاً استفاده شده است"}), 400
        category.slug = data["slug"]

    if "name" in data:
        category.name = data["name"]
    if "description" in data:
        category.description = data["description"]
    if "icon" in data:
        category.icon = data["icon"]
    if "sort_order" in data:
        category.sort_order = data["sort_order"]
    if "is_active" in data:
        category.is_active = data["is_active"]

    db.session.commit()
    return jsonify({"category": category.to_dict()})


@categories_bp.route("/categories/<int:cat_id>", methods=["DELETE"])
@jwt_required()
def delete_category(cat_id):
    category = Category.query.get_or_404(cat_id)
    if category.menu_items.count() > 0:
        return jsonify({"error": "این دسته‌بندی دارای آیتم است و قابل حذف نیست"}), 400
    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "دسته‌بندی حذف شد"})
