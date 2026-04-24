"""报表 Blueprint — /api/reports"""
from flask import Blueprint, request, g, send_file
from app.utils.response import success, error
from app.utils.auth import require_roles, require_auth
from app.services.report_service import ReportService
import io

bp = Blueprint("reports", __name__, url_prefix="/api/reports")
_svc = ReportService()


@bp.get("/course/<int:course_id>")
@require_roles("admin", "teacher", "counselor")
def course_stats(course_id):
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    result = _svc.get_course_stats(course_id, date_from, date_to)
    return success(result)


@bp.get("/student/<int:student_id>")
@require_auth
def student_history(student_id):
    # 学生只能查自己：通过 user_id 找到对应的 student.id 再比对
    if g.current_role == "student":
        from app.models.student import Student
        own = Student.query.filter_by(user_id=g.current_user_id).first()
        if own is None or own.id != student_id:
            return error("无权限查看他人记录", 403)
    result = _svc.get_student_history(student_id)
    return success(result)


@bp.get("/export")
@require_roles("admin", "teacher", "counselor")
def export_excel():
    filters = {
        "course_id": request.args.get("course_id"),
        "class_name": request.args.get("class_name"),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
    }
    file_bytes = _svc.export_excel(filters)
    return send_file(
        io.BytesIO(file_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="考勤报表.xlsx",
    )


@bp.get("/stats")
@require_auth
def dashboard_stats():
    """仪表盘统计数据"""
    return success(_svc.get_dashboard_stats())


@bp.get("/warnings")
@require_roles("admin", "counselor")
def get_warnings():
    result = _svc.get_warnings()
    return success(result)


@bp.post("/warnings/check")
@require_roles("admin")
def trigger_warning_check():
    """手动触发缺勤预警检查"""
    count = _svc.check_and_generate_warnings()
    return success({"new_warnings": count}, f"生成 {count} 条预警")
