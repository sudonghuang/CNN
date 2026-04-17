from .auth import bp as auth_bp
from .students import bp as students_bp
from .faces import bp as faces_bp
from .attendance import bp as attendance_bp
from .reports import bp as reports_bp
from .courses import bp as courses_bp

blueprints = [auth_bp, students_bp, faces_bp, attendance_bp, reports_bp, courses_bp]
