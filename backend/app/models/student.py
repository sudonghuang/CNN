"""学生与选课模型"""
from datetime import datetime
from app.extensions import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(50), nullable=False, index=True)
    department = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    face_registered = db.Column(db.Boolean, default=False)
    face_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系
    face_images = db.relationship("FaceImage", backref="student", lazy="dynamic",
                                  cascade="all, delete-orphan")
    attendance_records = db.relationship("AttendanceRecord", backref="student",
                                         lazy="dynamic")
    enrollments = db.relationship("StudentCourse", backref="student", lazy="dynamic",
                                  cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "class_name": self.class_name,
            "department": self.department,
            "face_registered": self.face_registered,
            "face_count": self.face_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Student {self.student_id} {self.name}>"


class StudentCourse(db.Model):
    __tablename__ = "student_courses"
    __table_args__ = (
        db.UniqueConstraint("student_id", "course_id", "semester", name="uk_enroll"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    semester = db.Column(db.String(20))


class FaceImage(db.Model):
    __tablename__ = "face_images"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False,
                           index=True)
    file_path = db.Column(db.String(255), nullable=False)
    is_processed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "file_path": self.file_path,
            "is_processed": self.is_processed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
