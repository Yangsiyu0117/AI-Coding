"""Audit log tests."""

from fastapi.testclient import TestClient


class TestAudit:
    def test_audit_requires_auth(self, client: TestClient):
        resp = client.get("/api/audit/")
        assert resp.status_code in (401, 403)

    def test_audit_list_empty(self, client: TestClient, admin_token):
        resp = client.get("/api/audit/", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_audit_records_after_environment_create(self, client: TestClient, admin_token):
        # Create an environment which should generate an audit log
        client.post(
            "/api/environments/",
            json={"name": "test-env", "description": "test", "ssh_default_port": 22},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = client.get("/api/audit/", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) >= 1
        assert logs[0]["action"] == "create_environment"
        assert logs[0]["target_type"] == "environment"
