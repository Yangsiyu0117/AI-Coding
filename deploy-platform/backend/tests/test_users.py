"""User CRUD tests."""

from fastapi.testclient import TestClient


class TestUserCRUD:
    def test_list_users_requires_admin(self, client: TestClient, operator_token):
        resp = client.get("/api/users/", headers={"Authorization": f"Bearer {operator_token}"})
        assert resp.status_code == 403

    def test_list_users(self, client: TestClient, admin_token):
        resp = client.get("/api/users/", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_user_role(self, client: TestClient, admin_token, operator_token):
        # Get operator user by listing
        resp = client.get("/api/users/", headers={"Authorization": f"Bearer {admin_token}"})
        users = resp.json()
        op_user = next((u for u in users if u["username"] == "operator"), None)
        assert op_user is not None

        resp = client.put(
            f"/api/users/{op_user['id']}",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_cannot_delete_self(self, client: TestClient, admin_token):
        resp = client.delete("/api/users/1", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400
        assert "own account" in resp.json()["detail"]

    def test_cannot_delete_last_admin(self, client: TestClient, admin_token):
        # Only one admin exists, cannot delete
        resp = client.delete("/api/users/2", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in (400, 404)
