class TestGetSettings:
    def test_get_settings(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        settings = resp.get_json()["settings"]
        assert "general" in settings
        assert settings["general"]["cafe_name"] == "موچی بار"

    def test_get_single_setting(self, client):
        resp = client.get("/api/settings/cafe_name")
        assert resp.status_code == 200
        assert resp.get_json()["setting"]["value"] == "موچی بار"

    def test_get_nonexistent_setting(self, client):
        resp = client.get("/api/settings/nonexistent")
        assert resp.status_code == 404


class TestUpdateSettings:
    def test_update_settings_bulk(self, client, auth_headers):
        resp = client.put(
            "/api/settings",
            headers=auth_headers,
            json={"cafe_name": "موچی بار آپدیت", "phone": "۰۲۱-۹۹۹۹۹۹۹۹"},
        )
        assert resp.status_code == 200

        resp = client.get("/api/settings/cafe_name")
        assert resp.get_json()["setting"]["value"] == "موچی بار آپدیت"

    def test_update_single_setting(self, client, auth_headers):
        resp = client.put(
            "/api/settings/cafe_name",
            headers=auth_headers,
            json={"value": "تک آیتم آپدیت"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["setting"]["value"] == "تک آیتم آپدیت"

    def test_create_new_setting(self, client, auth_headers):
        resp = client.put(
            "/api/settings/new_key",
            headers=auth_headers,
            json={"value": "مقدار جدید"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["setting"]["value"] == "مقدار جدید"

    def test_update_settings_missing_value(self, client, auth_headers):
        resp = client.put(
            "/api/settings/cafe_name",
            headers=auth_headers,
            json={"wrong_key": "test"},
        )
        assert resp.status_code == 400
