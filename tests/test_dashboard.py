class TestDashboard:
    def test_get_dashboard(self, client, auth_headers):
        resp = client.get("/api/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "stats" in data
        assert "recent_menu_items" in data
        assert "recent_gallery" in data
        stats = data["stats"]
        assert stats["total_menu_items"] >= 1
        assert stats["total_categories"] >= 1
        assert stats["total_gallery"] >= 1

    def test_dashboard_unauthenticated(self, client):
        resp = client.get("/api/dashboard")
        assert resp.status_code in (401, 422)
