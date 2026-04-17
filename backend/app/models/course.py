"""课程模型"""
from datetime import datetime
from app.extensions import db


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_name = db.Column(db.String(100), nullable=False)
    course_code = db.Column(db.String(20), unique=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False,
                           index=True)
    classroom = db.Column(db.String(50))
    schedule = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    tasks = db.relationship("AttendanceTask", backref="course", lazy="dynamic",
                            cascade="all, delete-orphan")
    enrollments = db.relationship("StudentCourse", backref="course", lazy="dynamic",
                                  cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "course_name": self.course_name,
            "course_code": self.course_code,
            "teacher_id": self.teacher_id,
            "classroom": self.classroom,
            "schedule": self.schedule,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Course {self.course_code} {self.course_name}>"
