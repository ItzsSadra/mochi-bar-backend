import io
import pytest
from app.models import db
from app.models.media import Media


MOCK_URL = "https://test-project.supabase.co/storage/v1/object/public/images"


class TestUpload:
    def test_upload_file(self, client, auth_headers):
        data = {
            "file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "test.png"),
            "folder": "menu",
        }
        resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        result = resp.get_json()
        assert "media" in result
        assert result["media"]["original_name"] == "test.png"
        assert result["media"]["folder"] == "menu"
        assert result["media"]["file_path"].startswith("https://")
        assert "menu/" in result["media"]["file_path"]
        assert result["url"].startswith("https://")

    def test_upload_stores_public_url(self, client, auth_headers):
        data = {
            "file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "photo.png"),
            "folder": "gallery",
        }
        resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        media_id = resp.get_json()["media"]["id"]
        media = db.session.get(Media, media_id)
        assert media.file_path.startswith("https://")
        assert "gallery/" in media.file_path

    def test_upload_with_alt_text(self, client, auth_headers):
        data = {
            "file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "alt.png"),
            "folder": "menu",
            "alt_text": "تست متن جایگزین",
        }
        resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        assert resp.get_json()["media"]["alt_text"] == "تست متن جایگزین"

    def test_upload_no_file(self, client, auth_headers):
        resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data={},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_upload_empty_filename(self, client, auth_headers):
        data = {
            "file": (io.BytesIO(b"test"), ""),
        }
        resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_upload_disallowed_extension(self, client, auth_headers):
        data = {
            "file": (io.BytesIO(b"script"), "hack.exe"),
        }
        resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_upload_unauthenticated(self, client):
        data = {
            "file": (io.BytesIO(b"test"), "test.png"),
        }
        resp = client.post(
            "/api/upload",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code in (401, 422)

    def test_upload_multiple_files(self, client, auth_headers):
        data = {
            "files": [
                (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10), "a.png"),
                (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10), "b.png"),
            ],
            "folder": "gallery",
        }
        resp = client.post(
            "/api/upload/multiple",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["count"] == 2
        for f in result["files"]:
            assert f["file_path"].startswith("https://")
            assert "gallery/" in f["file_path"]

    def test_upload_multiple_mixed_valid_invalid(self, client, auth_headers):
        data = {
            "files": [
                (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10), "good.png"),
                (io.BytesIO(b"bad"), "bad.exe"),
            ],
            "folder": "menu",
        }
        resp = client.post(
            "/api/upload/multiple",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["count"] == 1
        assert result["files"][0]["original_name"] == "good.png"

    def test_upload_default_folder(self, client, auth_headers):
        data = {
            "file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "no_folder.png"),
        }
        resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        assert resp.get_json()["media"]["folder"] == "default"


class TestMedia:
    def test_get_media(self, client, auth_headers):
        resp = client.get("/api/media", headers=auth_headers)
        assert resp.status_code == 200
        assert "media" in resp.get_json()

    def test_get_media_folders(self, client, auth_headers):
        resp = client.get("/api/media/folders", headers=auth_headers)
        assert resp.status_code == 200
        assert "folders" in resp.get_json()

    def test_get_media_with_folder_filter(self, client, auth_headers):
        resp = client.get("/api/media?folder=test", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_media_with_search(self, client, auth_headers):
        resp = client.get("/api/media?search=test", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_media_calls_supabase(self, client, auth_headers):
        upload_data = {
            "file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "delete_me.png"),
            "folder": "menu",
        }
        resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data=upload_data,
            content_type="multipart/form-data",
        )
        media_id = resp.get_json()["media"]["id"]

        resp = client.delete(f"/api/media/{media_id}", headers=auth_headers)
        assert resp.status_code == 200

        from app.models.media import Media
        assert db.session.get(Media, media_id) is None


class TestMediaUpdate:
    def test_update_alt_text(self, client, auth_headers):
        upload_data = {
            "file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "update.png"),
            "folder": "menu",
        }
        resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data=upload_data,
            content_type="multipart/form-data",
        )
        media_id = resp.get_json()["media"]["id"]

        resp = client.put(
            f"/api/media/{media_id}",
            headers=auth_headers,
            json={"alt_text": "متن جدید"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["media"]["alt_text"] == "متن جدید"
