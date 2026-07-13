class TestGetMenu:
    def test_get_all_menu(self, client):
        resp = client.get("/api/menu")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_get_menu_by_category(self, client):
        resp = client.get("/api/menu?category=mochi")
        assert resp.status_code == 200
        items = resp.get_json()["items"]
        assert all(i["category_slug"] == "mochi" for i in items)

    def test_get_menu_search(self, client):
        resp = client.get("/api/menu?search=شکلاتی")
        assert resp.status_code == 200
        items = resp.get_json()["items"]
        assert len(items) >= 1

    def test_get_menu_featured(self, client):
        resp = client.get("/api/menu?featured=true")
        assert resp.status_code == 200
        items = resp.get_json()["items"]
        assert all(i["is_featured"] for i in items)

    def test_get_menu_new(self, client):
        resp = client.get("/api/menu?new=true")
        assert resp.status_code == 200
        assert "items" in resp.get_json()


class TestGetMenuItem:
    def test_get_single_item(self, client):
        resp = client.get("/api/menu/1")
        assert resp.status_code == 200
        item = resp.get_json()["item"]
        assert item["name"] == "موچی شکلاتی"
        assert item["price"] == 85000

    def test_get_nonexistent_item(self, client):
        resp = client.get("/api/menu/9999")
        assert resp.status_code == 404


class TestCreateMenuItem:
    def test_create_item_success(self, client, auth_headers):
        resp = client.post(
            "/api/menu",
            headers=auth_headers,
            json={
                "name": "موچی جدید",
                "price": 70000,
                "category_id": 1,
                "description": "تست ایجاد",
            },
        )
        assert resp.status_code == 201
        item = resp.get_json()["item"]
        assert item["name"] == "موچی جدید"
        assert item["price"] == 70000

    def test_create_item_missing_fields(self, client, auth_headers):
        resp = client.post(
            "/api/menu",
            headers=auth_headers,
            json={"name": "بدون قیمت"},
        )
        assert resp.status_code == 400

    def test_create_item_unauthenticated(self, client):
        resp = client.post(
            "/api/menu",
            json={"name": "تست", "price": 10000, "category_id": 1},
        )
        assert resp.status_code in (401, 422)


class TestUpdateMenuItem:
    def test_update_item_success(self, client, auth_headers):
        resp = client.put(
            "/api/menu/1",
            headers=auth_headers,
            json={"name": "موچی شکلاتی آپدیت", "price": 95000},
        )
        assert resp.status_code == 200
        item = resp.get_json()["item"]
        assert item["name"] == "موچی شکلاتی آپدیت"
        assert item["price"] == 95000

    def test_update_item_partial(self, client, auth_headers):
        resp = client.put(
            "/api/menu/1",
            headers=auth_headers,
            json={"is_featured": False},
        )
        assert resp.status_code == 200
        assert resp.get_json()["item"]["is_featured"] is False

    def test_update_nonexistent_item(self, client, auth_headers):
        resp = client.put(
            "/api/menu/9999",
            headers=auth_headers,
            json={"name": "test"},
        )
        assert resp.status_code == 404


class TestDeleteMenuItem:
    def test_delete_item_success(self, client, auth_headers):
        resp = client.delete("/api/menu/1", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_nonexistent_item(self, client, auth_headers):
        resp = client.delete("/api/menu/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestMenuItemImageUrl:
    def test_create_item_with_image_url(self, client, auth_headers):
        resp = client.post(
            "/api/menu",
            headers=auth_headers,
            json={
                "name": "موچی با تصویر",
                "price": 80000,
                "category_id": 1,
                "image_url": "https://test.supabase.co/storage/v1/object/public/images/menu/test.png",
            },
        )
        assert resp.status_code == 201
        item = resp.get_json()["item"]
        assert item["image_url"] == "https://test.supabase.co/storage/v1/object/public/images/menu/test.png"

    def test_create_item_without_image_url(self, client, auth_headers):
        resp = client.post(
            "/api/menu",
            headers=auth_headers,
            json={
                "name": "موچی بدون تصویر",
                "price": 60000,
                "category_id": 1,
            },
        )
        assert resp.status_code == 201
        item = resp.get_json()["item"]
        assert item["image_url"] is None

    def test_update_item_image_url(self, client, auth_headers):
        resp = client.put(
            "/api/menu/1",
            headers=auth_headers,
            json={"image_url": "https://test.supabase.co/storage/v1/object/public/images/menu/updated.png"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["item"]["image_url"] == "https://test.supabase.co/storage/v1/object/public/images/menu/updated.png"

        resp = client.get("/api/menu/1")
        assert resp.get_json()["item"]["image_url"] == "https://test.supabase.co/storage/v1/object/public/images/menu/updated.png"

    def test_menu_item_image_url_in_list(self, client, auth_headers):
        client.post(
            "/api/menu",
            headers=auth_headers,
            json={
                "name": "موچی لیست",
                "price": 75000,
                "category_id": 1,
                "image_url": "https://test.supabase.co/storage/v1/object/public/images/menu/list.png",
            },
        )
        resp = client.get("/api/menu")
        items = resp.get_json()["items"]
        matches = [i for i in items if i["name"] == "موچی لیست"]
        assert len(matches) == 1
        assert matches[0]["image_url"] == "https://test.supabase.co/storage/v1/object/public/images/menu/list.png"

    def test_upload_then_create_menu_item(self, client, auth_headers):
        import io
        upload_resp = client.post(
            "/api/upload",
            headers=auth_headers,
            data={
                "file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100), "menu_photo.png"),
                "folder": "menu",
            },
            content_type="multipart/form-data",
        )
        assert upload_resp.status_code == 201
        image_url = upload_resp.get_json()["url"]

        create_resp = client.post(
            "/api/menu",
            headers=auth_headers,
            json={
                "name": "موچی آپلود شده",
                "price": 90000,
                "category_id": 1,
                "image_url": image_url,
            },
        )
        assert create_resp.status_code == 201
        item = create_resp.get_json()["item"]
        assert item["image_url"] == image_url

        get_resp = client.get(f"/api/menu/{item['id']}")
        assert get_resp.get_json()["item"]["image_url"] == image_url
