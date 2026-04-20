"""考勤业务逻辑"""
import io
from datetime import datetime, date
from typing import Optional
from flask import current_app
from app.extensions import db
from app.models.attendance import AttendanceTask, AttendanceRecord
from app.models.student import StudentCourse


# 内存去重集合：{task_id: set(student_db_id)}
_recognized_cache: dict = {}


class AttendanceService:

    # ── 任务管理 ────────────────────────────────────────────────

    def create_task(self, data: dict) -> dict:
        course_id = data.get("course_id")
        teacher_id = data.get("teacher_id")
        task_date_str = data.get("task_date") or date.today().isoformat()
        if not course_id:
            return {"ok": False, "code": 400, "message": "course_id 不能为空"}
        try:
            task_date = date.fromisoformat(task_date_str)
        except ValueError:
            return {"ok": False, "code": 400, "message": "task_date 格式错误，应为 YYYY-MM-DD"}
        task = AttendanceTask(
            course_id=course_id, teacher_id=teacher_id,
            task_date=task_date, status="pending",
        )
        db.session.add(task)
        db.session.commit()
        return {"ok": True, "data": task.to_dict()}

    def start_task(self, task_id: int, operator_id: int) -> dict:
        task = AttendanceTask.query.get(task_id)
        if not task:
            return {"ok": False, "code": 404, "message": "任务不存在"}
        if task.status == "running":
            return {"ok": False, "code": 409, "message": "任务已在运行中"}
        if task.status == "finished":
            return {"ok": False, "code": 409, "message": "任务已结束，不可重新开始"}
        enrolled = StudentCourse.query.filter_by(course_id=task.course_id).count()
        task.status = "running"
        task.start_time = datetime.utcnow()
        task.total_students = enrolled
        _recognized_cache[task_id] = set()
        db.session.commit()
        return {"ok": True, "data": task.to_dict()}

    def stop_task(self, task_id: int, operator_id: int) -> dict:
        task = AttendanceTask.query.get(task_id)
        if not task:
            return {"ok": False, "code": 404, "message": "任务不存在"}
        if task.status != "running":
            return {"ok": False, "code": 409, "message": "任务未在运行中"}
        self._finalize_task(task)
        _recognized_cache.pop(task_id, None)
        return {"ok": True, "data": task.to_dict()}

    def _finalize_task(self, task: AttendanceTask) -> None:
        enrolled_ids = {
            sc.student_id for sc in
            StudentCourse.query.filter_by(course_id=task.course_id).all()
        }
        recognized_ids = {
            r.student_id for r in
            AttendanceRecord.query.filter_by(task_id=task.id).all()
        }
        absent_ids = enrolled_ids - recognized_ids
        for sid in absent_ids:
            db.session.add(AttendanceRecord(
                task_id=task.id, student_id=sid,
                status="absent", confidence=0.0,
            ))
        task.status = "finished"
        task.end_time = datetime.utcnow()
        task.present_count = len(recognized_ids)
        db.session.commit()

    # ── 识别帧处理 ─────────────────────────────────────────────

    def process_frame(self, task_id: int, image_bytes: bytes) -> dict:
        task = AttendanceTask.query.get(task_id)
        if not task or task.status != "running":
            return {"ok": False, "code": 409, "message": "任务未在运行中"}
        import cv2
        import numpy as np
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"ok": False, "code": 422, "message": "图像解码失败"}
        try:
            from app.ai.model_manager import ModelManager
            mgr = ModelManager.get_instance()
            results = mgr.recognize_faces(img)
        except Exception as e:
            current_app.logger.error("Inference error: %s", e)
            return {"ok": False, "code": 500, "message": "识别服务异常"}

        written = []
        for r in results:
            if r.get("status") in ("present", "unverified"):
                self._record_if_new(task_id, r)
                written.append(r)
        return {"ok": True, "data": written}

    def _record_if_new(self, task_id: int, recognition: dict) -> None:
        student_db_id = recognition.get("student_db_id")
        if student_db_id is None:
            return
        cache = _recognized_cache.setdefault(task_id, set())
        if student_db_id in cache:
            return
        cache.add(student_db_id)
        existing = AttendanceRecord.query.filter_by(
            task_id=task_id, student_id=student_db_id
        ).first()
        if existing:
            return
        rec = AttendanceRecord(
            task_id=task_id,
            student_id=student_db_id,
            status=recognition.get("status", "present"),
            confidence=recognition.get("confidence", 0.0),
            recognized_at=datetime.utcnow(),
        )
        db.session.add(rec)
        # 实时更新 task.present_count，供 WebSocket task_update 使用
        task = AttendanceTask.query.get(task_id)
        if task and recognition.get("status") in ("present", "unverified"):
            task.present_count = (task.present_count or 0) + 1
        db.session.commit()

    # ── 查询与修正 ─────────────────────────────────────────────

    def get_tasks(self, page: int, per_page: int, filters: dict) -> dict:
        q = AttendanceTask.query
        if filters.get("course_id"):
            q = q.filter_by(course_id=int(filters["course_id"]))
        if filters.get("teacher_id"):
            q = q.filter_by(teacher_id=int(filters["teacher_id"]))
        if filters.get("status"):
            q = q.filter_by(status=filters["status"])
        if filters.get("date_from"):
            try:
                from datetime import date
                q = q.filter(AttendanceTask.task_date >= date.fromisoformat(filters["date_from"]))
            except ValueError:
                pass
        if filters.get("date_to"):
            try:
                from datetime import date
                q = q.filter(AttendanceTask.task_date <= date.fromisoformat(filters["date_to"]))
            except ValueError:
                pass
        pagination = q.order_by(AttendanceTask.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return {"items": [t.to_dict() for t in pagination.items],
                "total": pagination.total}

    def get_task_detail(self, task_id: int) -> Optional[dict]:
        task = AttendanceTask.query.get(task_id)
        if not task:
            return None
        data = task.to_dict()
        records = AttendanceRecord.query.filter_by(task_id=task_id).all()
        data["records"] = [r.to_dict() for r in records]
        return data

    def get_records(self, page: int, per_page: int, filters: dict) -> dict:
        from app.models.student import Student
        from app.models.user import User
        q = AttendanceRecord.query
        if filters.get("task_id"):
            q = q.filter_by(task_id=int(filters["task_id"]))
        if filters.get("status"):
            q = q.filter_by(status=filters["status"])
        if filters.get("course_id"):
            q = q.join(AttendanceTask, AttendanceRecord.task_id == AttendanceTask.id)\
                 .filter(AttendanceTask.course_id == int(filters["course_id"]))
        if filters.get("date_from"):
            try:
                from datetime import date
                q = q.join(AttendanceTask, AttendanceRecord.task_id == AttendanceTask.id,
                           isouter=True)\
                     .filter(AttendanceTask.task_date >= date.fromisoformat(filters["date_from"]))
            except (ValueError, Exception):
                pass
        if filters.get("current_user_id"):
            user = User.query.get(int(filters["current_user_id"]))
            if user:
                st = Student.query.filter_by(user_id=user.id).first()
                if st:
                    q = q.filter_by(student_id=st.id)
        pagination = q.order_by(AttendanceRecord.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return {"items": [r.to_dict() for r in pagination.items],
                "total": pagination.total}

    def update_record(self, record_id: int, status: str, operator_id: int,
                      note: str = None) -> dict:
        rec = AttendanceRecord.query.get(record_id)
        if not rec:
            return {"ok": False, "code": 404, "message": "记录不存在"}
        rec.status = status
        rec.verified_by = operator_id
        if note is not None:
            rec.note = note
        db.session.commit()
        return {"ok": True, "data": rec.to_dict()}
