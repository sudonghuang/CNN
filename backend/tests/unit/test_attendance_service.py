"""单元测试：AttendanceService（考勤业务逻辑）"""
import pytest
from unittest.mock import patch, MagicMock


def _make_task(task_id=1, status="pending", course_id=1, total_students=3):
    task = MagicMock()
    task.id = task_id
    task.status = status
    task.course_id = course_id
    task.total_students = total_students
    task.present_count = 0
    task.to_dict.return_value = {
        "id": task_id, "status": status,
        "course_id": course_id, "total_students": total_students,
    }
    return task


class TestCreateTask:
    def test_missing_course_id_returns_error(self, app):
        with app.app_context():
            from app.services.attendance_service import AttendanceService
            svc = AttendanceService()
            result = svc.create_task({"teacher_id": 1})
            assert not result["ok"]
            assert result["code"] == 400

    def test_invalid_date_returns_error(self, app):
        with app.app_context():
            from app.services.attendance_service import AttendanceService
            svc = AttendanceService()
            result = svc.create_task({"course_id": 1, "task_date": "not-a-date"})
            assert not result["ok"]
            assert result["code"] == 400


class TestStartTask:
    def test_start_already_running_returns_409(self, app):
        with app.app_context():
            from app.services.attendance_service import AttendanceService
            svc = AttendanceService()
            task = _make_task(status="running")
            with patch("app.services.attendance_service.AttendanceTask") as MockTask:
                MockTask.query.get.return_value = task
                result = svc.start_task(1, operator_id=1)
            assert not result["ok"]
            assert result["code"] == 409

    def test_start_finished_returns_409(self, app):
        with app.app_context():
            from app.services.attendance_service import AttendanceService
            svc = AttendanceService()
            task = _make_task(status="finished")
            with patch("app.services.attendance_service.AttendanceTask") as MockTask:
                MockTask.query.get.return_value = task
                result = svc.start_task(1, operator_id=1)
            assert not result["ok"]
            assert result["code"] == 409

    def test_start_nonexistent_returns_404(self, app):
        with app.app_context():
            from app.services.attendance_service import AttendanceService
            svc = AttendanceService()
            with patch("app.services.attendance_service.AttendanceTask") as MockTask:
                MockTask.query.get.return_value = None
                result = svc.start_task(999, operator_id=1)
            assert not result["ok"]
            assert result["code"] == 404


class TestUpdateRecord:
    def test_update_nonexistent_returns_404(self, app):
        with app.app_context():
            from app.services.attendance_service import AttendanceService
            svc = AttendanceService()
            with patch("app.services.attendance_service.AttendanceRecord") as MockRecord:
                MockRecord.query.get.return_value = None
                result = svc.update_record(999, "present", operator_id=1)
            assert not result["ok"]
            assert result["code"] == 404
