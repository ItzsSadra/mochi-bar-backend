class TestGetCategories:
    def test_get_categories(self, client):
        resp = client.get("/api/categories")
        assert resp.status_code == 200
        cats = resp.get_json()["categories"]
        assert len(cats) >= 1
        assert cats[0]["name"] == "موچی"

    def test_get_single_category(self, client):
        resp = client.get("/api/categories/1")
        assert resp.status_code == 200
        cat = resp.get_json()["category"]
        assert cat["slug"] == "mochi"


class TestCreateCategory:
    def test_create_category_success(self, client, auth_headers):
        resp = client.post(
            "/api/categories",
            headers=auth_headers,
            json={"name": "نوشیدنی گرم", "slug": "hot-drinks", "icon": "☕"},
        )
        assert resp.status_code == 201
        cat = resp.get_json()["category"]
        assert cat["name"] == "نوشیدنی گرم"
        assert cat["slug"] == "hot-drinks"

    def test_create_category_missing_name(self, client, auth_headers):
        resp = client.post(
            "/api/categories",
            headers=auth_headers,
            json={"slug": "test"},
        )
        assert resp.status_code == 400

    def test_create_category_duplicate_slug(self, client, auth_headers):
        resp = client.post(
            "/api/categories",
            headers=auth_headers,
            json={"name": "موچی ۲", "slug": "mochi"},
        )
        assert resp.status_code == 400


class TestUpdateCategory:
    def test_update_category_success(self, client, auth_headers):
        resp = client.put(
            "/api/categories/1",
            headers=auth_headers,
            json={"name": "موچی آپدیت", "is_active": False},
        )
        assert resp.status_code == 200
        cat = resp.get_json()["category"]
        assert cat["name"] == "موچی آپدیت"
        assert cat["is_active"] is False

    def test_update_nonexistent_category(self, client, auth_headers):
        resp = client.put(
            "/api/categories/9999",
            headers=auth_headers,
            json={"name": "test"},
        )
        assert resp.status_code == 404


class TestDeleteCategory:
    def test_delete_empty_category(self, client, auth_headers):
        resp = client.post(
            "/api/categories",
            headers=auth_headers,
            json={"name": "قابل حذف", "slug": "deletable"},
        )
        cat_id = resp.get_json()["category"]["id"]
        resp = client.delete(f"/api/categories/{cat_id}", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_category_with_items(self, client, auth_headers):
        resp = client.delete("/api/categories/1", headers=auth_headers)
        assert resp.status_code == 400
