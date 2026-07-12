import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force SQLite before any app import reads .env
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["SECRET_KEY"] = "test-secret"

from app import create_app
from app.models import db as _db
import app.models.user  # noqa: ensure models registered
import app.models.category  # noqa
import app.models.menu_item  # noqa
import app.models.gallery  # noqa
import app.models.setting  # noqa
import app.models.media  # noqa


@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config.pop("SQLALCHEMY_ENGINE_OPTIONS", None)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(autouse=True)
def reset_db(app):
    """Roll back every test so they don't interfere with each other."""
    with app.app_context():
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        _seed_test_data()
        yield
        _db.session.rollback()


@pytest.fixture(scope="function")
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def auth_headers(client):
    resp = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = resp.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


MOCK_SUPABASE_URL = "https://test-project.supabase.co/storage/v1/object/public/images"


@pytest.fixture(autouse=True)
def mock_supabase(monkeypatch):
    """Mock Supabase storage calls so tests never hit the real API."""
    from unittest.mock import MagicMock

    def fake_upload(folder, filename, data, content_type):
        return f"{MOCK_SUPABASE_URL}/{folder}/{filename}"

    def fake_delete(path):
        pass

    monkeypatch.setattr("app.routes.upload.upload_to_storage", fake_upload)
    monkeypatch.setattr("app.routes.media.delete_from_storage", fake_delete)


def _seed_test_data():
    from app.models.user import User
    from app.models.category import Category
    from app.models.menu_item import MenuItem
    from app.models.gallery import GalleryImage
    from app.models.setting import Setting

    admin = User(username="admin", email="admin@test.com", display_name="Admin")
    admin.set_password("admin123")
    _db.session.add(admin)

    cat = Category(name="موچی", slug="mochi", icon="🍡", sort_order=0)
    _db.session.add(cat)
    _db.session.flush()

    item = MenuItem(
        name="موچی شکلاتی",
        description="تست",
        price=85000,
        category_id=cat.id,
        is_featured=True,
        is_new=False,
        is_available=True,
    )
    _db.session.add(item)

    img = GalleryImage(
        title="تست",
        image_url="/uploads/test.jpg",
        is_active=True,
    )
    _db.session.add(img)

    setting = Setting(key="cafe_name", value="موچی بار", group="general")
    _db.session.add(setting)

    _db.session.commit()
