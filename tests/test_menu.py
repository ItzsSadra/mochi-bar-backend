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
