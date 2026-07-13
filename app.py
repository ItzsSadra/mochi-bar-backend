import os
import uuid
import logging
from datetime import datetime, timezone, timedelta

from flask import Flask, request, jsonify, redirect, send_from_directory, make_response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv = None
try:
    from dotenv import load_dotenv as _load_dotenv
    load_dotenv = _load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "mochi-cafe-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/mochi_cafe",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    if os.getenv("DATABASE_URL", "").startswith("postgresql"):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_size": 10,
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {}
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "mochi-cafe-jwt-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    UPLOAD_FOLDER = "/tmp/uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "images")


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------

_supabase_client: Client | None = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        _supabase_client = create_client(url, key)
    return _supabase_client


def upload_to_storage(folder: str, filename: str, data: bytes, content_type: str) -> str:
    path = f"{folder}/{filename}"
    supabase = get_supabase()
    bucket = Config.SUPABASE_BUCKET
    supabase.storage.from_(bucket).upload(
        path, data, {"content-type": content_type, "cache-control": "3600"},
    )
    return supabase.storage.from_(bucket).get_public_url(path)


def delete_from_storage(path: str) -> None:
    try:
        get_supabase().storage.from_(Config.SUPABASE_BUCKET).remove([path])
    except Exception:
        logging.getLogger(__name__).warning("Failed to delete from Supabase: %s", path, exc_info=True)


def extract_storage_path(file_path: str) -> str | None:
    prefix = f"/storage/v1/object/public/{Config.SUPABASE_BUCKET}/"
    if prefix in file_path:
        return file_path.split(prefix, 1)[1]
    return None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(120), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="admin")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id, "username": self.username, "email": self.email,
            "display_name": self.display_name, "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    menu_items = db.relationship("MenuItem", backref="category", lazy="select")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "slug": self.slug,
            "description": self.description, "icon": self.icon,
            "sort_order": self.sort_order, "is_active": self.is_active,
            "item_count": len(self.menu_items) if self.menu_items else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MenuItem(db.Model):
    __tablename__ = "menu_items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    ingredients = db.Column(db.Text, nullable=True)
    preparation_time = db.Column(db.Integer, nullable=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    is_new = db.Column(db.Boolean, nullable=False, default=False)
    is_available = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    gallery_images = db.relationship("MenuGalleryImage", backref="menu_item", lazy="select", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "price": self.price, "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "category_slug": self.category.slug if self.category else None,
            "image_url": self.image_url, "ingredients": self.ingredients,
            "preparation_time": self.preparation_time,
            "is_featured": self.is_featured, "is_new": self.is_new,
            "is_available": self.is_available, "sort_order": self.sort_order,
            "gallery_images": [img.to_dict() for img in self.gallery_images],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MenuGalleryImage(db.Model):
    __tablename__ = "menu_gallery_images"
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "menu_item_id": self.menu_item_id,
            "image_url": self.image_url, "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GalleryImage(db.Model):
    __tablename__ = "gallery_images"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    caption = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "caption": self.caption,
            "image_url": self.image_url, "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Setting(db.Model):
    __tablename__ = "settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    group = db.Column(db.String(50), nullable=False, default="general")
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "key": self.key, "value": self.value,
            "group": self.group,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Media(db.Model):
    __tablename__ = "media"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    folder = db.Column(db.String(100), nullable=False, default="default")
    alt_text = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "filename": self.filename,
            "original_name": self.original_name, "file_path": self.file_path,
            "file_size": self.file_size, "mime_type": self.mime_type,
            "folder": self.folder, "alt_text": self.alt_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = [
    ("cafe_name", "موچی بار", "general"),
    ("cafe_slogan", "تجربه‌ای متفاوت از طعم و هنر", "general"),
    ("address", "تهران، خیابان ولیعصر، نبش کوچه گل", "contact"),
    ("phone", "۰۲۱-۱۲۳۴۵۶۷۸", "contact"),
    ("instagram", "@mochi_cafe", "contact"),
    ("telegram", "@mochi_cafe", "contact"),
    ("working_hours", "هر روز ۸ صبح تا ۱۱ شب", "contact"),
    ("about_text", "موچی بار با الهام از هنر و فرهنگ ژاپنی، فضایی آرام و متفاوت برای لحظات شما خلق کرده است. ما با استفاده از بهترین مواد اولیه و تکنیک‌های نوین، نوشیدنی‌ها و دسرهایی منحصربه‌فرد ارائه می‌دهیم.", "about"),
    ("hero_text", "لذت طعم اصیل ژاپنی", "hero"),
    ("hero_subtext", "موچی، بستنی، نوشیدنی و دسرهای دست‌ساز با کیفیت بی‌نظیر", "hero"),
    ("footer_text", "© ۱۴۰۵ موچی بار. تمامی حقوق محفوظ است.", "footer"),
    ("primary_color", "#6B8F71", "theme"),
    ("accent_color", "#F8C8D4", "theme"),
]

DEFAULT_CATEGORIES = [
    {"name": "موچی", "slug": "mochi", "icon": "🍡", "sort_order": 0},
    {"name": "نوشیدنی گرم", "slug": "hot-drinks", "icon": "☕", "sort_order": 1},
    {"name": "نوشیدنی سرد", "slug": "cold-drinks", "icon": "🧊", "sort_order": 2},
    {"name": "کیک", "slug": "cake", "icon": "🍰", "sort_order": 3},
    {"name": "دسر", "slug": "dessert", "icon": "🍮", "sort_order": 4},
    {"name": "بستنی", "slug": "ice-cream", "icon": "🍦", "sort_order": 5},
    {"name": "ویژه", "slug": "special", "icon": "⭐", "sort_order": 6},
]

DEFAULT_MENU_ITEMS = []

_seeded = False


def _seed_data():
    global _seeded
    if _seeded:
        return
    _seeded = True

    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", email="admin@mochicafe.ir", display_name="مدیر سیستم", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    for key, value, group in DEFAULT_SETTINGS:
        if not Setting.query.filter_by(key=key).first():
            db.session.add(Setting(key=key, value=value, group=group))

    category_map = {}
    for cat_data in DEFAULT_CATEGORIES:
        existing = Category.query.filter_by(slug=cat_data["slug"]).first()
        if not existing:
            cat = Category(**cat_data)
            db.session.add(cat)
            db.session.flush()
            category_map[cat_data["slug"]] = cat.id
        else:
            category_map[cat_data["slug"]] = existing.id

    for item_data in DEFAULT_MENU_ITEMS:
        slug = item_data["category_slug"]
        cat_id = category_map.get(slug)
        if cat_id and not MenuItem.query.filter_by(name=item_data["name"]).first():
            fields = {k: v for k, v in item_data.items() if k != "category_slug"}
            db.session.add(MenuItem(category_id=cat_id, **fields))

    db.session.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _safe_folder(folder):
    folder = secure_filename(folder)
    if not folder or folder.startswith("."):
        folder = "default"
    return folder


def _escape_like(value):
    return value.replace("%", "\\%").replace("_", "\\_")


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


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

_app_initialized = False


def create_app():
    global _app_initialized
    app = Flask(__name__)
    app.config.from_object(Config)

    raw = os.getenv("CORS_ORIGINS", "").strip()
    allowed_origins = [o.strip() for o in raw.split(",") if o.strip()] if raw else ["*"]

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin", "*")
        if "*" in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        elif origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = allowed_origins[0] if allowed_origins else "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = make_response()
            response.status_code = 204
            return response

    db.init_app(app)
    JWTManager(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()
        _seed_data()

    # ---- Error handlers ----

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "یافت نشد"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "روش مجاز نیست"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return jsonify({"error": "خطای داخلی سرور"}), 500

    # ---- Auth ----

    @app.route("/api/login", methods=["POST"])
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
        token = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=24))
        return jsonify({"token": token, "user": user.to_dict()})

    @app.route("/api/me", methods=["GET"])
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

    @app.route("/api/change-password", methods=["POST"])
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

    # ---- Categories ----

    @app.route("/api/categories", methods=["GET"])
    def get_categories():
        categories = Category.query.order_by(Category.sort_order, Category.id).all()
        return jsonify({"categories": [c.to_dict() for c in categories]})

    @app.route("/api/categories/<int:cat_id>", methods=["GET"])
    def get_category(cat_id):
        category = Category.query.get_or_404(cat_id)
        return jsonify({"category": category.to_dict()})

    @app.route("/api/categories", methods=["POST"])
    @jwt_required()
    def create_category():
        data = request.get_json()
        if not data:
            return jsonify({"error": "داده‌ای ارسال نشد"}), 400
        if not data.get("name"):
            return jsonify({"error": "نام دسته‌بندی الزامی است"}), 400
        slug = data.get("slug") or data["name"].replace(" ", "-")
        if Category.query.filter_by(slug=slug).first():
            return jsonify({"error": "این دسته‌بندی قبلاً ایجاد شده است"}), 400
        category = Category(name=data["name"], slug=slug, description=data.get("description", ""),
                            icon=data.get("icon"), sort_order=data.get("sort_order", 0),
                            is_active=data.get("is_active", True))
        db.session.add(category)
        db.session.commit()
        return jsonify({"category": category.to_dict()}), 201

    @app.route("/api/categories/<int:cat_id>", methods=["PUT"])
    @jwt_required()
    def update_category(cat_id):
        category = Category.query.get_or_404(cat_id)
        data = request.get_json()
        if not data:
            return jsonify({"error": "داده‌ای ارسال نشد"}), 400
        if "slug" in data:
            if Category.query.filter(Category.slug == data["slug"], Category.id != cat_id).first():
                return jsonify({"error": "این نامک قبلاً استفاده شده است"}), 400
            category.slug = data["slug"]
        for field in ("name", "description", "icon", "sort_order", "is_active"):
            if field in data:
                setattr(category, field, data[field])
        db.session.commit()
        return jsonify({"category": category.to_dict()})

    @app.route("/api/categories/<int:cat_id>", methods=["DELETE"])
    @jwt_required()
    def delete_category(cat_id):
        category = Category.query.get_or_404(cat_id)
        if category.menu_items.count() > 0:
            return jsonify({"error": "این دسته‌بندی دارای آیتم است و قابل حذف نیست"}), 400
        db.session.delete(category)
        db.session.commit()
        return jsonify({"message": "دسته‌بندی حذف شد"})

    # ---- Menu ----

    @app.route("/api/menu", methods=["GET"])
    def get_menu_items():
        category = request.args.get("category")
        search = request.args.get("search")
        featured = request.args.get("featured")
        new = request.args.get("new")
        query = MenuItem.query.options(db.joinedload(MenuItem.category), db.joinedload(MenuItem.gallery_images))
        if category:
            query = query.join(MenuItem.category).filter(
                db.or_(MenuItem.category.has(slug=category), MenuItem.category.has(name=category))
            )
        if search:
            safe = _escape_like(search)
            query = query.filter(db.or_(MenuItem.name.ilike(f"%{safe}%"), MenuItem.description.ilike(f"%{safe}%")))
        if featured == "true":
            query = query.filter_by(is_featured=True)
        if new == "true":
            query = query.filter_by(is_new=True)
        query = query.order_by(MenuItem.sort_order, MenuItem.id.desc())
        return jsonify({"items": [i.to_dict() for i in query.all()]})

    @app.route("/api/menu/<int:item_id>", methods=["GET"])
    def get_menu_item(item_id):
        return jsonify({"item": MenuItem.query.get_or_404(item_id).to_dict()})

    @app.route("/api/menu", methods=["POST"])
    @jwt_required()
    def create_menu_item():
        data = request.get_json()
        if not data:
            return jsonify({"error": "داده‌ای ارسال نشد"}), 400
        if not data.get("name") or not data.get("price") or not data.get("category_id"):
            return jsonify({"error": "نام، قیمت و دسته‌بندی الزامی است"}), 400
        if not isinstance(data["price"], (int, float)) or data["price"] <= 0:
            return jsonify({"error": "قیمت باید عدد مثبت باشد"}), 400
        if not Category.query.get(data["category_id"]):
            return jsonify({"error": "دسته‌بندی یافت نشد"}), 400
        item = MenuItem(name=data["name"], description=data.get("description", ""), price=data["price"],
                        category_id=data["category_id"], image_url=data.get("image_url"),
                        ingredients=data.get("ingredients"), preparation_time=data.get("preparation_time"),
                        is_featured=data.get("is_featured", False), is_new=data.get("is_new", False),
                        is_available=data.get("is_available", True), sort_order=data.get("sort_order", 0))
        db.session.add(item)
        db.session.commit()
        return jsonify({"item": item.to_dict()}), 201

    @app.route("/api/menu/<int:item_id>", methods=["PUT"])
    @jwt_required()
    def update_menu_item(item_id):
        item = MenuItem.query.get_or_404(item_id)
        data = request.get_json()
        if not data:
            return jsonify({"error": "داده‌ای ارسال نشد"}), 400
        if "price" in data and (not isinstance(data["price"], (int, float)) or data["price"] <= 0):
            return jsonify({"error": "قیمت باید عدد مثبت باشد"}), 400
        if "category_id" in data and not Category.query.get(data["category_id"]):
            return jsonify({"error": "دسته‌بندی یافت نشد"}), 400
        for field in ("name", "description", "price", "category_id", "image_url", "ingredients",
                       "preparation_time", "is_featured", "is_new", "is_available", "sort_order"):
            if field in data:
                setattr(item, field, data[field])
        db.session.commit()
        return jsonify({"item": item.to_dict()})

    @app.route("/api/menu/<int:item_id>", methods=["DELETE"])
    @jwt_required()
    def delete_menu_item(item_id):
        item = MenuItem.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "آیتم منو حذف شد"})

    @app.route("/api/menu/<int:item_id>/gallery", methods=["POST"])
    @jwt_required()
    def add_menu_gallery_image(item_id):
        MenuItem.query.get_or_404(item_id)
        data = request.get_json()
        if not data or not data.get("image_url"):
            return jsonify({"error": "آدرس تصویر الزامی است"}), 400
        max_order = db.session.query(db.func.max(MenuGalleryImage.sort_order)).filter_by(menu_item_id=item_id).scalar() or 0
        image = MenuGalleryImage(menu_item_id=item_id, image_url=data["image_url"],
                                 sort_order=data.get("sort_order", max_order + 1))
        db.session.add(image)
        db.session.commit()
        return jsonify({"image": image.to_dict()}), 201

    @app.route("/api/menu/<int:item_id>/gallery/<int:image_id>", methods=["DELETE"])
    @jwt_required()
    def delete_menu_gallery_image(item_id, image_id):
        image = MenuGalleryImage.query.filter_by(id=image_id, menu_item_id=item_id).first_or_404()
        db.session.delete(image)
        db.session.commit()
        return jsonify({"message": "تصویر گالری حذف شد"})

    # ---- Gallery ----

    @app.route("/api/gallery", methods=["GET"])
    def get_gallery():
        images = GalleryImage.query.filter_by(is_active=True).order_by(GalleryImage.sort_order, GalleryImage.id.desc()).all()
        return jsonify({"images": [i.to_dict() for i in images]})

    @app.route("/api/gallery/<int:image_id>", methods=["GET"])
    def get_gallery_image(image_id):
        return jsonify({"image": GalleryImage.query.filter_by(id=image_id, is_active=True).first_or_404().to_dict()})

    @app.route("/api/gallery", methods=["POST"])
    @jwt_required()
    def create_gallery_image():
        data = request.get_json()
        if not data or not data.get("image_url"):
            return jsonify({"error": "آدرس تصویر الزامی است"}), 400
        max_order = db.session.query(db.func.max(GalleryImage.sort_order)).scalar() or 0
        image = GalleryImage(title=data.get("title"), caption=data.get("caption"),
                             image_url=data["image_url"], sort_order=data.get("sort_order", max_order + 1),
                             is_active=data.get("is_active", True))
        db.session.add(image)
        db.session.commit()
        return jsonify({"image": image.to_dict()}), 201

    @app.route("/api/gallery/<int:image_id>", methods=["PUT"])
    @jwt_required()
    def update_gallery_image(image_id):
        image = GalleryImage.query.get_or_404(image_id)
        data = request.get_json()
        if not data:
            return jsonify({"error": "داده‌ای ارسال نشد"}), 400
        for field in ("title", "caption", "image_url", "sort_order", "is_active"):
            if field in data:
                setattr(image, field, data[field])
        db.session.commit()
        return jsonify({"image": image.to_dict()})

    @app.route("/api/gallery/<int:image_id>", methods=["DELETE"])
    @jwt_required()
    def delete_gallery_image(image_id):
        image = GalleryImage.query.get_or_404(image_id)
        db.session.delete(image)
        db.session.commit()
        return jsonify({"message": "تصویر گالری حذف شد"})

    # ---- Settings ----

    @app.route("/api/settings", methods=["GET"])
    def get_settings():
        settings = Setting.query.all()
        result = {}
        for s in settings:
            result.setdefault(s.group, {})[s.key] = s.value
        return jsonify({"settings": result})

    @app.route("/api/settings", methods=["PUT"])
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
                db.session.add(Setting(key=key, value=str(value)))
        db.session.commit()
        return jsonify({"message": "تنظیمات با موفقیت ذخیره شد"})

    @app.route("/api/settings/<key>", methods=["GET"])
    def get_setting(key):
        setting = Setting.query.filter_by(key=key).first()
        if not setting:
            return jsonify({"error": "تنظیم یافت نشد"}), 404
        return jsonify({"setting": setting.to_dict()})

    @app.route("/api/settings/<key>", methods=["PUT"])
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

    # ---- Dashboard ----

    @app.route("/api/dashboard", methods=["GET"])
    @jwt_required()
    def get_dashboard():
        return jsonify({
            "stats": {
                "total_menu_items": MenuItem.query.count(),
                "total_categories": Category.query.count(),
                "total_gallery": GalleryImage.query.count(),
                "featured_items": MenuItem.query.filter_by(is_featured=True).count(),
                "available_items": MenuItem.query.filter_by(is_available=True).count(),
                "new_items": MenuItem.query.filter_by(is_new=True).count(),
            },
            "recent_menu_items": [i.to_dict() for i in MenuItem.query.order_by(MenuItem.id.desc()).limit(5).all()],
            "recent_gallery": [i.to_dict() for i in GalleryImage.query.order_by(GalleryImage.id.desc()).limit(5).all()],
        })

    # ---- Upload ----

    @app.route("/api/upload", methods=["POST"])
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
        content_type = file.content_type or f"image/{ext}"

        try:
            public_url = upload_to_storage(folder, filename, file_data, content_type)
        except Exception:
            logging.getLogger(__name__).exception("Supabase upload failed")
            return jsonify({"error": "خطا در آپلود فایل"}), 500

        media = Media(filename=filename, original_name=original_name, file_path=public_url,
                      file_size=len(file_data), mime_type=content_type, folder=folder,
                      alt_text=request.form.get("alt_text"))
        db.session.add(media)
        db.session.commit()
        return jsonify({"media": media.to_dict(), "url": public_url}), 201

    @app.route("/api/upload/multiple", methods=["POST"])
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
            content_type = file.content_type or f"image/{ext}"
            try:
                public_url = upload_to_storage(folder, filename, file_data, content_type)
            except Exception:
                continue
            media = Media(filename=filename, original_name=original_name, file_path=public_url,
                          file_size=len(file_data), mime_type=content_type, folder=folder)
            db.session.add(media)
            uploaded.append(media)
        db.session.commit()
        return jsonify({"files": [m.to_dict() for m in uploaded], "count": len(uploaded)}), 201

    @app.route("/api/uploads/<folder>/<filename>", methods=["GET"])
    def serve_upload(folder, filename):
        folder = _safe_folder(folder)
        filename = secure_filename(filename)
        supabase_url = app.config.get("SUPABASE_URL")
        if supabase_url:
            try:
                url = get_supabase().storage.from_(Config.SUPABASE_BUCKET).get_public_url(f"{folder}/{filename}")
                return redirect(url, code=302)
            except Exception:
                pass
        return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], folder), filename)

    # ---- Media ----

    @app.route("/api/media", methods=["GET"])
    @jwt_required()
    def get_media():
        folder = request.args.get("folder")
        search = request.args.get("search")
        query = Media.query
        if folder:
            query = query.filter_by(folder=folder)
        if search:
            safe = _escape_like(search)
            query = query.filter(db.or_(Media.original_name.ilike(f"%{safe}%"), Media.alt_text.ilike(f"%{safe}%")))
        return jsonify({"media": [m.to_dict() for m in query.order_by(Media.id.desc()).all()]})

    @app.route("/api/media/<int:media_id>", methods=["PUT"])
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

    @app.route("/api/media/<int:media_id>", methods=["DELETE"])
    @jwt_required()
    def delete_media(media_id):
        media = Media.query.get_or_404(media_id)
        storage_path = extract_storage_path(media.file_path)
        if storage_path:
            delete_from_storage(storage_path)
        db.session.delete(media)
        db.session.commit()
        return jsonify({"message": "فایل حذف شد"})

    @app.route("/api/media/folders", methods=["GET"])
    @jwt_required()
    def get_folders():
        folders = db.session.query(Media.folder).distinct().all()
        return jsonify({"folders": [f[0] for f in folders]})

    # ---- Contact form ----

    @app.route("/api/contact", methods=["POST"])
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
        logging.getLogger(__name__).info(
            "Contact form submission: name=%s, phone=%s, message=%s",
            name, data.get("phone", ""), message[:100],
        )
        return jsonify({"message": "پیام شما با موفقیت دریافت شد"}), 201

    # ---- Health check ----

    @app.route("/api/health", methods=["GET"])
    def health_check():
        try:
            db.session.execute(db.text("SELECT 1"))
            return jsonify({"status": "ok", "database": "connected"})
        except Exception:
            return jsonify({"status": "degraded", "database": "disconnected"}), 503

    return app


# ---------------------------------------------------------------------------
# Vercel entry point
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
    )
