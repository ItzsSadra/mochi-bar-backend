from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models import db
from app.models.menu_item import MenuItem, MenuGalleryImage
from app.models.category import Category

menu_bp = Blueprint("menu", __name__)


def _escape_like(value):
    return value.replace("%", "\\%").replace("_", "\\_")


@menu_bp.route("/menu", methods=["GET"])
def get_menu_items():
    category = request.args.get("category")
    search = request.args.get("search")
    featured = request.args.get("featured")
    new = request.args.get("new")

    query = MenuItem.query

    if category:
        query = query.join(MenuItem.category).filter(
            db.or_(
                MenuItem.category.has(slug=category),
                MenuItem.category.has(name=category),
            )
        )
    if search:
        safe = _escape_like(search)
        query = query.filter(
            db.or_(
                MenuItem.name.ilike(f"%{safe}%"),
                MenuItem.description.ilike(f"%{safe}%"),
            )
        )
    if featured == "true":
        query = query.filter_by(is_featured=True)
    if new == "true":
        query = query.filter_by(is_new=True)

    query = query.order_by(MenuItem.sort_order, MenuItem.id.desc())
    items = query.all()
    return jsonify({"items": [item.to_dict() for item in items]})


@menu_bp.route("/menu/<int:item_id>", methods=["GET"])
def get_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return jsonify({"item": item.to_dict()})


@menu_bp.route("/menu", methods=["POST"])
@jwt_required()
def create_menu_item():
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400
    if not data.get("name") or not data.get("price") or not data.get("category_id"):
        return jsonify({"error": "نام، قیمت و دسته‌بندی الزامی است"}), 400

    if not isinstance(data["price"], (int, float)) or data["price"] <= 0:
        return jsonify({"error": "قیمت باید عدد مثبت باشد"}), 400

    category = db.session.get(Category, data["category_id"])
    if not category:
        return jsonify({"error": "دسته‌بندی یافت نشد"}), 400

    item = MenuItem(
        name=data["name"],
        description=data.get("description", ""),
        price=data["price"],
        category_id=data["category_id"],
        image_url=data.get("image_url"),
        ingredients=data.get("ingredients"),
        preparation_time=data.get("preparation_time"),
        is_featured=data.get("is_featured", False),
        is_new=data.get("is_new", False),
        is_available=data.get("is_available", True),
        sort_order=data.get("sort_order", 0),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"item": item.to_dict()}), 201


@menu_bp.route("/menu/<int:item_id>", methods=["PUT"])
@jwt_required()
def update_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400

    if "name" in data:
        item.name = data["name"]
    if "description" in data:
        item.description = data["description"]
    if "price" in data:
        if not isinstance(data["price"], (int, float)) or data["price"] <= 0:
            return jsonify({"error": "قیمت باید عدد مثبت باشد"}), 400
        item.price = data["price"]
    if "category_id" in data:
        category = db.session.get(Category, data["category_id"])
        if not category:
            return jsonify({"error": "دسته‌بندی یافت نشد"}), 400
        item.category_id = data["category_id"]
    if "image_url" in data:
        item.image_url = data["image_url"]
    if "ingredients" in data:
        item.ingredients = data["ingredients"]
    if "preparation_time" in data:
        item.preparation_time = data["preparation_time"]
    if "is_featured" in data:
        item.is_featured = data["is_featured"]
    if "is_new" in data:
        item.is_new = data["is_new"]
    if "is_available" in data:
        item.is_available = data["is_available"]
    if "sort_order" in data:
        item.sort_order = data["sort_order"]

    db.session.commit()
    return jsonify({"item": item.to_dict()})


@menu_bp.route("/menu/<int:item_id>", methods=["DELETE"])
@jwt_required()
def delete_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "آیتم منو حذف شد"})


@menu_bp.route("/menu/<int:item_id>/gallery", methods=["POST"])
@jwt_required()
def add_menu_gallery_image(item_id):
    item = MenuItem.query.get_or_404(item_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "داده‌ای ارسال نشد"}), 400

    if not data.get("image_url"):
        return jsonify({"error": "آدرس تصویر الزامی است"}), 400

    max_order = db.session.query(db.func.max(MenuGalleryImage.sort_order)).filter_by(
        menu_item_id=item_id
    ).scalar() or 0

    image = MenuGalleryImage(
        menu_item_id=item_id,
        image_url=data["image_url"],
        sort_order=data.get("sort_order", max_order + 1),
    )
    db.session.add(image)
    db.session.commit()
    return jsonify({"image": image.to_dict()}), 201


@menu_bp.route("/menu/<int:item_id>/gallery/<int:image_id>", methods=["DELETE"])
@jwt_required()
def delete_menu_gallery_image(item_id, image_id):
    image = MenuGalleryImage.query.filter_by(id=image_id, menu_item_id=item_id).first_or_404()
    db.session.delete(image)
    db.session.commit()
    return jsonify({"message": "تصویر گالری حذف شد"})
