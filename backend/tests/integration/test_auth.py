"""集成测试：认证接口 /api/auth"""
import pytest
from tests.conftest import auth_header


class TestLogin:
    def test_login_success(self, client, admin_user):
        """登录成功应返回 access_token"""
        resp = client.post("/api/auth/login", json={
            "username": "admin_test", "password": "Test@123456"
        })
        data = resp.get_json()
        assert resp.status_code == 200
        assert "token" in data["data"]
        assert data["data"]["user"]["role"] == "admin"

    def test_login_wrong_password(self, client, admin_user):
        """错误密码应返回 401"""
        resp = client.post("/api/auth/login", json={
            "username": "admin_test", "password": "wrongpassword"
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """不存在的用户应返回 401"""
        resp = client.post("/api/auth/login", json={
            "username": "nobody", "password": "any"
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        """缺少字段应返回 400"""
        resp = client.post("/api/auth/login", json={"username": "admin_test"})
        assert resp.status_code == 400

    def test_login_empty_body(self, client):
        """空请求体应返回 400"""
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 400


class TestChangePassword:
    def test_change_password_success(self, client, admin_user):
        """正确的旧密码应允许修改"""
        resp = client.put(
            "/api/auth/password",
            json={"old_password": "Test@123456", "new_password": "NewPass@123"},
            headers=auth_header(admin_user["token"]),
        )
        assert resp.status_code == 200

    def test_change_password_wrong_old(self, client, admin_user):
        """错误的旧密码应返回 400 或 401"""
        resp = client.put(
            "/api/auth/password",
            json={"old_password": "WrongOld@123", "new_password": "NewPass@123"},
            headers=auth_header(admin_user["token"]),
        )
        assert resp.status_code in (400, 401)

    def test_change_password_unauthenticated(self, client):
        """未认证请求应返回 401"""
        resp = client.put(
            "/api/auth/password",
            json={"old_password": "Test@123456", "new_password": "NewPass@123"},
        )
        assert resp.status_code == 401
