class TestLogin:
    def test_login_success(self, client):
        resp = client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

    def test_login_wrong_password(self, client):
        resp = client.post(
            "/api/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/api/login", json={"username": "admin"})
        assert resp.status_code == 400

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/login",
            json={"username": "nobody", "password": "pass"},
        )
        assert resp.status_code == 401


class TestGetMe:
    def test_get_me_authenticated(self, client, auth_headers):
        resp = client.get("/api/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["user"]["username"] == "admin"

    def test_get_me_unauthenticated(self, client):
        resp = client.get("/api/me")
        assert resp.status_code in (401, 422)


class TestChangePassword:
    def test_change_password_success(self, client, auth_headers):
        resp = client.post(
            "/api/change-password",
            headers=auth_headers,
            json={"current_password": "admin123", "new_password": "newpass456"},
        )
        assert resp.status_code == 200

    def test_change_password_wrong_current(self, client, auth_headers):
        resp = client.post(
            "/api/change-password",
            headers=auth_headers,
            json={"current_password": "wrong", "new_password": "newpassword123"},
        )
        assert resp.status_code == 401

    def test_change_password_missing_fields(self, client, auth_headers):
        resp = client.post(
            "/api/change-password",
            headers=auth_headers,
            json={"current_password": "admin123"},
        )
        assert resp.status_code == 400
