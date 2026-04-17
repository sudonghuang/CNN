"""课程管理 Blueprint — /api/courses"""
from flask import Blueprint, request, g
from app.extensions import db
from app.models.course import Course
from app.models.student import StudentCourse
from app.utils.response import success, error, paginated
from app.utils.auth import require_roles, require_auth

bp = Blueprint("courses", __name__, url_prefix="/api/courses")


@bp.get("")
@require_auth
def list_courses():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    q = Course.query
    if request.args.get("teacher_id"):
        q = q.filter_by(teacher_id=int(request.args["teacher_id"]))
    # 教师只能看自己的课程
    if g.current_role == "teacher":
        q = q.filter_by(teacher_id=g.current_user_id)
    pagination = q.order_by(Course.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return paginated([c.to_dict() for c in pagination.items],
                     pagination.total, page, per_page)


@bp.post("")
@require_roles("admin", "teacher")
def create_course():
    data = request.get_json(silent=True) or {}
    course_name = data.get("course_name") or data.get("name")
    course_code = data.get("course_code")
    if not course_name:
        return error("course_name 不能为空", 400)
    if course_code and Course.query.filter_by(course_code=course_code).first():
        return error("课程编号已存在", 409)
    teacher_id = data.get("teacher_id") or g.current_user_id
    course = Course(
        course_name=course_name,
        course_code=course_code,
        teacher_id=teacher_id,
        classroom=data.get("classroom"),
        schedule=data.get("schedule"),
    )
    db.session.add(course)
    db.session.commit()
    return success(course.to_dict(), code=201)


@bp.get("/<int:course_id>")
@require_auth
def get_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        return error("课程不存在", 404)
    data = course.to_dict()
    # 附带选课学生数
    data["enrolled_count"] = StudentCourse.query.filter_by(
        course_id=course_id
    ).count()
    return success(data)


@bp.put("/<int:course_id>")
@require_roles("admin", "teacher")
def update_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        return error("课程不存在", 404)
    # 教师只能修改自己的课程
    if g.current_role == "teacher" and course.teacher_id != g.current_user_id:
        return error("无权修改他人课程", 403)
    data = request.get_json(silent=True) or {}
    for field in ("course_name", "course_code", "classroom", "schedule"):
        if field in data:
            setattr(course, field, data[field])
    db.session.commit()
    return success(course.to_dict())


@bp.delete("/<int:course_id>")
@require_roles("admin")
def delete_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        return error("课程不存在", 404)
    db.session.delete(course)
    db.session.commit()
    return success({"id": course_id})


# ── 选课管理 ──────────────────────────────────────────────────────────

@bp.post("/<int:course_id>/enroll")
@require_roles("admin", "counselor")
def enroll_student(course_id):
    """将学生加入课程"""
    course = db.session.get(Course, course_id)
    if not course:
        return error("课程不存在", 404)
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    if not student_id:
        return error("student_id 不能为空", 400)
    existing = StudentCourse.query.filter_by(
        course_id=course_id, student_id=student_id
    ).first()
    if existing:
        return error("该学生已在课程中", 409)
    db.session.add(StudentCourse(course_id=course_id, student_id=student_id))
    db.session.commit()
    return success({"course_id": course_id, "student_id": student_id}, code=201)


@bp.delete("/<int:course_id>/enroll/<int:student_id>")
@require_roles("admin", "counselor")
def unenroll_student(course_id, student_id):
    """将学生从课程移除"""
    record = StudentCourse.query.filter_by(
        course_id=course_id, student_id=student_id
    ).first()
    if not record:
        return error("选课记录不存在", 404)
    db.session.delete(record)
    db.session.commit()
    return success({"course_id": course_id, "student_id": student_id})


@bp.get("/<int:course_id>/students")
@require_auth
def list_enrolled_students(course_id):
    """获取课程的选课学生列表"""
    course = db.session.get(Course, course_id)
    if not course:
        return error("课程不存在", 404)
    from app.models.student import Student
    students = (
        db.session.query(Student)
        .join(StudentCourse, StudentCourse.student_id == Student.id)
        .filter(StudentCourse.course_id == course_id)
        .all()
    )
    return success([s.to_dict() for s in students])
