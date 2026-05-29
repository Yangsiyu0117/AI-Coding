"""Health and patrol API tests."""

from fastapi.testclient import TestClient


class TestHealth:
    def test_health_anonymous(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestPatrol:
    def test_patrol_requires_auth(self, client: TestClient):
        resp = client.post("/api/patrol/run", json={"environment_id": 1})
        assert resp.status_code in (401, 403)

    def test_patrol_empty_environment(self, client: TestClient, admin_token):
        resp = client.post(
            "/api/patrol/run",
            json={"environment_id": 1},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_nodes"] == 0
        assert data["healthy_nodes"] == 0
        assert data["unhealthy_nodes"] == 0
