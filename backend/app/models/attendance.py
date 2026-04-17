"""考勤任务与考勤记录模型"""
from datetime import datetime
from app.extensions import db


class AttendanceTask(db.Model):
    __tablename__ = "attendance_tasks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False,
                          index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False,
                           index=True)
    task_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(
        db.Enum("pending", "running", "finished"), default="pending", index=True
    )
    total_students = db.Column(db.Integer, default=0)
    present_count = db.Column(db.Integer, default=0)
    model_version = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    records = db.relationship("AttendanceRecord", backref="task", lazy="dynamic",
                              cascade="all, delete-orphan")

    def get_attendance_rate(self) -> float:
        if not self.total_students:
            return 0.0
        return round(self.present_count / self.total_students, 4)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "course_id": self.course_id,
            "teacher_id": self.teacher_id,
            "task_date": self.task_date.isoformat() if self.task_date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "total_students": self.total_students,
            "present_count": self.present_count,
            "attendance_rate": self.get_attendance_rate(),
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    __table_args__ = (
        db.UniqueConstraint("task_id", "student_id", name="uk_task_student"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey("attendance_tasks.id"),
                        nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False,
                           index=True)
    status = db.Column(
        db.Enum("present", "absent", "unverified"), nullable=False, index=True
    )
    confidence = db.Column(db.Float, default=0.0)
    recognized_at = db.Column(db.DateTime)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    note = db.Column(db.String(200))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "student_id": self.student_id,
            "status": self.status,
            "confidence": self.confidence,
            "recognized_at": self.recognized_at.isoformat()
            if self.recognized_at
            else None,
            "verified_by": self.verified_by,
            "note": self.note,
        }
