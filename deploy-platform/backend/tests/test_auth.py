"""Auth endpoint tests."""

import pytest
from fastapi.testclient import TestClient


class TestLogin:
    def test_login_invalid_user(self, client: TestClient):
        resp = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
        assert resp.status_code == 401

    def test_login_success(self, client: TestClient, admin_token):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert data["token_type"] == "bearer"


class TestRegister:
    def test_register_creates_user(self, client: TestClient):
        resp = client.post("/api/auth/register", json={"username": "newuser", "password": "pass123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["role"] == "admin"  # first user is admin

    def test_register_duplicate(self, client: TestClient, admin_token):
        resp = client.post("/api/auth/register", json={"username": "admin", "password": "x"})
        assert resp.status_code == 409

    def test_register_second_user_is_operator(self, client: TestClient, admin_token):
        resp = client.post("/api/auth/register", json={"username": "op1", "password": "pass", "role": "operator"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "operator"
