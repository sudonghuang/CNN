"""用户模型"""
import bcrypt
from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(
        db.Enum("admin", "teacher", "counselor", "student"), nullable=False
    )
    real_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    courses = db.relationship("Course", backref="teacher", lazy="dynamic",
                              foreign_keys="Course.teacher_id")
    tasks = db.relationship("AttendanceTask", backref="teacher", lazy="dynamic",
                            foreign_keys="AttendanceTask.teacher_id")

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "real_name": self.real_name,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
