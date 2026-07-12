class TestGetGallery:
    def test_get_gallery(self, client):
        resp = client.get("/api/gallery")
        assert resp.status_code == 200
        images = resp.get_json()["images"]
        assert len(images) >= 1
        assert images[0]["title"] == "تست"

    def test_get_single_image(self, client):
        resp = client.get("/api/gallery/1")
        assert resp.status_code == 200
        assert resp.get_json()["image"]["image_url"] == "/uploads/test.jpg"


class TestCreateGalleryImage:
    def test_create_image_success(self, client, auth_headers):
        resp = client.post(
            "/api/gallery",
            headers=auth_headers,
            json={"title": "تصویر جدید", "image_url": "/uploads/new.jpg"},
        )
        assert resp.status_code == 201
        img = resp.get_json()["image"]
        assert img["title"] == "تصویر جدید"

    def test_create_image_missing_url(self, client, auth_headers):
        resp = client.post(
            "/api/gallery",
            headers=auth_headers,
            json={"title": "بدون آدرس"},
        )
        assert resp.status_code == 400


class TestUpdateGalleryImage:
    def test_update_image_success(self, client, auth_headers):
        resp = client.put(
            "/api/gallery/1",
            headers=auth_headers,
            json={"title": "آپدیت شده", "caption": "کپشن جدید"},
        )
        assert resp.status_code == 200
        img = resp.get_json()["image"]
        assert img["title"] == "آپدیت شده"
        assert img["caption"] == "کپشن جدید"


class TestDeleteGalleryImage:
    def test_delete_image_success(self, client, auth_headers):
        resp = client.delete("/api/gallery/1", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_nonexistent_image(self, client, auth_headers):
        resp = client.delete("/api/gallery/9999", headers=auth_headers)
        assert resp.status_code == 404
