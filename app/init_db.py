import logging
from app.models import db
from app.models.user import User
from app.models.category import Category
from app.models.menu_item import MenuItem
from app.models.gallery import GalleryImage
from app.models.setting import Setting

logger = logging.getLogger(__name__)


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


def initialize_database():
    from flask import current_app

    with current_app.app_context():
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if "users" not in existing_tables:
            db.create_all()
            print("Database tables created successfully.")
        else:
            print("Database tables already exist. Skipping creation.")

        _disable_rls()
        _seed_data()


def _disable_rls():
    tables_to_disable_rls = [
        "users",
        "categories",
        "menu_items",
        "menu_gallery_images",
        "gallery_images",
        "settings",
        "media",
    ]
    for table in tables_to_disable_rls:
        try:
            db.session.execute(db.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
        except Exception as e:
            logger.warning("RLS disable failed for %s: %s", table, e)
    db.session.commit()
    print("Row Level Security disabled for all application tables.")


def _seed_data():
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@mochicafe.ir",
            display_name="مدیر سیستم",
            role="admin",
        )
        admin.set_password("admin123")
        db.session.add(admin)
        print("Default admin account created (admin / admin123)")

    for key, value, group in DEFAULT_SETTINGS:
        existing = Setting.query.filter_by(key=key).first()
        if not existing:
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
            item = MenuItem(category_id=cat_id, **fields)
            db.session.add(item)

    db.session.commit()
    print("Seed data inserted successfully.")
