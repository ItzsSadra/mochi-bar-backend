from app.models import db
from app.models.user import User
from app.models.category import Category
from app.models.menu_item import MenuItem
from app.models.gallery import GalleryImage
from app.models.setting import Setting
from app.models.media import Media


def test_models_exist():
    assert User.__tablename__ == "users"
    assert Category.__tablename__ == "categories"
    assert MenuItem.__tablename__ == "menu_items"
    assert GalleryImage.__tablename__ == "gallery_images"
    assert Setting.__tablename__ == "settings"
    assert Media.__tablename__ == "media"


def test_user_password_hashing(app):
    with app.app_context():
        user = User(username="test", email="test@test.com")
        user.set_password("secret")
        assert user.check_password("secret") is True
        assert user.check_password("wrong") is False
        assert user.password_hash != "secret"


def test_user_to_dict(app):
    with app.app_context():
        user = User(username="test", email="test@test.com", display_name="Test")
        user.set_password("pass")
        d = user.to_dict()
        assert d["username"] == "test"
        assert d["email"] == "test@test.com"
        assert "password_hash" not in d


def test_category_to_dict(app):
    with app.app_context():
        cat = Category(name="تست", slug="test", icon="🍵")
        d = cat.to_dict()
        assert d["name"] == "تست"
        assert d["slug"] == "test"


def test_menu_item_to_dict(app):
    with app.app_context():
        item = MenuItem(name="تست", price=50000, category_id=1)
        d = item.to_dict()
        assert d["name"] == "تست"
        assert d["price"] == 50000


def test_gallery_image_to_dict(app):
    with app.app_context():
        img = GalleryImage(title="تست", image_url="/uploads/test.jpg")
        d = img.to_dict()
        assert d["title"] == "تست"
        assert d["image_url"] == "/uploads/test.jpg"


def test_setting_to_dict(app):
    with app.app_context():
        s = Setting(key="test", value="مقدار")
        d = s.to_dict()
        assert d["key"] == "test"
        assert d["value"] == "مقدار"


def test_media_to_dict(app):
    with app.app_context():
        m = Media(filename="test.png", original_name="test.png", file_path="/uploads/test.png")
        d = m.to_dict()
        assert d["filename"] == "test.png"
        assert d["original_name"] == "test.png"
