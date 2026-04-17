"""集成测试：学生管理接口 /api/students"""
import pytest
from tests.conftest import auth_header


def _create_student(client, token, data=None):
    payload = data or {
        "student_id": "2024001",
        "name": "张三",
        "class_name": "计科2401",
        "gender": "male",
    }
    return client.post(
        "/api/students",
        json=payload,
        headers=auth_header(token),
    )


class TestStudentList:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/students")
        assert resp.status_code == 401

    def test_list_returns_paginated(self, client, admin_user):
        resp = client.get("/api/students", headers=auth_header(admin_user["token"]))
        data = resp.get_json()
        assert resp.status_code == 200
        assert "items" in data["data"]
        assert "pagination" in data["data"]


class TestCreateStudent:
    def test_create_success(self, client, admin_user):
        resp = _create_student(client, admin_user["token"])
        assert resp.status_code == 201
        data = resp.get_json()["data"]
        assert data["student_id"] == "2024001"
        assert data["name"] == "张三"

    def test_create_duplicate_student_id(self, client, admin_user):
        _create_student(client, admin_user["token"])
        resp = _create_student(client, admin_user["token"])
        assert resp.status_code == 409

    def test_create_missing_required_fields(self, client, admin_user):
        resp = client.post(
            "/api/students",
            json={"name": "李四"},  # 缺少 student_id
            headers=auth_header(admin_user["token"]),
        )
        assert resp.status_code == 400

    def test_create_requires_admin_or_counselor(self, client, teacher_user):
        resp = _create_student(client, teacher_user["token"])
        # 教师无权创建学生
        assert resp.status_code == 403


class TestGetStudent:
    def test_get_existing(self, client, admin_user):
        create_resp = _create_student(client, admin_user["token"])
        sid = create_resp.get_json()["data"]["id"]
        resp = client.get(f"/api/students/{sid}",
                          headers=auth_header(admin_user["token"]))
        assert resp.status_code == 200
        assert resp.get_json()["data"]["student_id"] == "2024001"

    def test_get_nonexistent(self, client, admin_user):
        resp = client.get("/api/students/99999",
                          headers=auth_header(admin_user["token"]))
        assert resp.status_code == 404


class TestUpdateStudent:
    def test_update_name(self, client, admin_user):
        sid = _create_student(client, admin_user["token"]).get_json()["data"]["id"]
        resp = client.put(
            f"/api/students/{sid}",
            json={"name": "张三改名"},
            headers=auth_header(admin_user["token"]),
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["name"] == "张三改名"


class TestDeleteStudent:
    def test_delete_existing(self, client, admin_user):
        sid = _create_student(client, admin_user["token"]).get_json()["data"]["id"]
        resp = client.delete(f"/api/students/{sid}",
                             headers=auth_header(admin_user["token"]))
        assert resp.status_code == 200
        get_resp = client.get(f"/api/students/{sid}",
                              headers=auth_header(admin_user["token"]))
        assert get_resp.status_code == 404
