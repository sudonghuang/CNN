"""集成测试：考勤接口 /api/attendance"""
import pytest
from tests.conftest import auth_header


def _setup_course_and_task(client, token, app):
    """辅助：创建课程 → 创建考勤任务，返回 task_id"""
    from app.extensions import db
    from app.models.course import Course
    from app.models.user import User

    with app.app_context():
        # 获取 teacher user id
        teacher = User.query.filter_by(username="teacher_test").first()
        if not teacher:
            teacher = User(username="teacher_test", role="teacher", real_name="T")
            teacher.set_password("Test@123456")
            db.session.add(teacher)
            db.session.commit()
        teacher_id = teacher.id

        course = Course(
            course_code="CS101", course_name="计算机基础", teacher_id=teacher_id,
        )
        db.session.add(course)
        db.session.commit()
        course_id = course.id

    resp = client.post(
        "/api/attendance/tasks",
        json={"course_id": course_id, "task_date": "2024-09-01"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]["id"], course_id


class TestAttendanceTasks:
    def test_list_tasks_requires_auth(self, client):
        resp = client.get("/api/attendance/tasks")
        assert resp.status_code == 401

    def test_create_task_success(self, client, teacher_user, app):
        task_id, _ = _setup_course_and_task(client, teacher_user["token"], app)
        assert isinstance(task_id, int)

    def test_create_task_missing_course(self, client, teacher_user):
        resp = client.post(
            "/api/attendance/tasks",
            json={"task_date": "2024-09-01"},
            headers=auth_header(teacher_user["token"]),
        )
        assert resp.status_code == 400

    def test_get_task_detail(self, client, teacher_user, app):
        task_id, _ = _setup_course_and_task(client, teacher_user["token"], app)
        resp = client.get(f"/api/attendance/tasks/{task_id}",
                          headers=auth_header(teacher_user["token"]))
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "pending"

    def test_get_nonexistent_task(self, client, teacher_user):
        resp = client.get("/api/attendance/tasks/99999",
                          headers=auth_header(teacher_user["token"]))
        assert resp.status_code == 404

    def test_start_task(self, client, teacher_user, app):
        task_id, _ = _setup_course_and_task(client, teacher_user["token"], app)
        resp = client.post(f"/api/attendance/tasks/{task_id}/start",
                           headers=auth_header(teacher_user["token"]))
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "running"

    def test_start_already_running(self, client, teacher_user, app):
        task_id, _ = _setup_course_and_task(client, teacher_user["token"], app)
        client.post(f"/api/attendance/tasks/{task_id}/start",
                    headers=auth_header(teacher_user["token"]))
        resp = client.post(f"/api/attendance/tasks/{task_id}/start",
                           headers=auth_header(teacher_user["token"]))
        assert resp.status_code == 409

    def test_stop_task(self, client, teacher_user, app):
        task_id, _ = _setup_course_and_task(client, teacher_user["token"], app)
        client.post(f"/api/attendance/tasks/{task_id}/start",
                    headers=auth_header(teacher_user["token"]))
        resp = client.post(f"/api/attendance/tasks/{task_id}/stop",
                           headers=auth_header(teacher_user["token"]))
        assert resp.status_code == 200
        assert resp.get_json()["data"]["status"] == "finished"


class TestAttendanceRecords:
    def test_list_records_requires_auth(self, client):
        resp = client.get("/api/attendance/records")
        assert resp.status_code == 401

    def test_update_record_invalid_status(self, client, teacher_user):
        resp = client.put(
            "/api/attendance/records/1",
            json={"status": "invalid_status"},
            headers=auth_header(teacher_user["token"]),
        )
        assert resp.status_code == 400

    def test_update_nonexistent_record(self, client, teacher_user):
        resp = client.put(
            "/api/attendance/records/99999",
            json={"status": "present"},
            headers=auth_header(teacher_user["token"]),
        )
        assert resp.status_code == 404
