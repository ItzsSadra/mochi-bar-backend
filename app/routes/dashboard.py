from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.models import db
from app.models.menu_item import MenuItem
from app.models.category import Category
from app.models.gallery import GalleryImage
from app.models.user import User

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def get_dashboard():
    total_menu_items = MenuItem.query.count()
    total_categories = Category.query.count()
    total_gallery = GalleryImage.query.count()
    featured_items = MenuItem.query.filter_by(is_featured=True).count()
    available_items = MenuItem.query.filter_by(is_available=True).count()
    new_items = MenuItem.query.filter_by(is_new=True).count()

    recent_items = MenuItem.query.order_by(MenuItem.id.desc()).limit(5).all()
    recent_gallery = GalleryImage.query.order_by(GalleryImage.id.desc()).limit(5).all()

    return jsonify({
        "stats": {
            "total_menu_items": total_menu_items,
            "total_categories": total_categories,
            "total_gallery": total_gallery,
            "featured_items": featured_items,
            "available_items": available_items,
            "new_items": new_items,
        },
        "recent_menu_items": [item.to_dict() for item in recent_items],
        "recent_gallery": [img.to_dict() for img in recent_gallery],
    })
