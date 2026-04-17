"""考勤 Blueprint — /api/attendance"""
import base64
from flask import Blueprint, request, g
from app.utils.response import success, error, paginated
from app.utils.auth import require_roles, require_auth
from app.services.attendance_service import AttendanceService

bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")
_svc = AttendanceService()


# ── 考勤任务 ──────────────────────────────────────────────────────

@bp.post("/tasks")
@require_roles("admin", "teacher")
def create_task():
    data = request.get_json(silent=True) or {}
    data["teacher_id"] = g.current_user_id
    result = _svc.create_task(data)
    if result["ok"]:
        return success(result["data"], code=201)
    return error(result["message"], result["code"])


@bp.get("/tasks")
@require_roles("admin", "teacher", "counselor")
def list_tasks():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    filters = {
        "course_id": request.args.get("course_id"),
        "teacher_id": g.current_user_id if g.current_role == "teacher" else None,
        "status": request.args.get("status"),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
    }
    result = _svc.get_tasks(page, per_page, filters)
    return paginated(result["items"], result["total"], page, per_page)


@bp.get("/tasks/<int:task_id>")
@require_roles("admin", "teacher", "counselor")
def get_task(task_id):
    result = _svc.get_task_detail(task_id)
    if result:
        return success(result)
    return error("考勤任务不存在", 404)


@bp.post("/tasks/<int:task_id>/start")
@require_roles("admin", "teacher")
def start_task(task_id):
    result = _svc.start_task(task_id, g.current_user_id)
    if result["ok"]:
        return success(result["data"])
    return error(result["message"], result["code"])


@bp.post("/tasks/<int:task_id>/stop")
@require_roles("admin", "teacher")
def stop_task(task_id):
    result = _svc.stop_task(task_id, g.current_user_id)
    if result["ok"]:
        return success(result["data"])
    return error(result["message"], result["code"])


@bp.post("/tasks/<int:task_id>/recognize")
@require_roles("admin", "teacher")
def recognize_frame(task_id):
    """REST 方式提交单帧识别（WebSocket 不可用时的降级方案）"""
    data = request.get_json(silent=True) or {}
    image_b64 = data.get("image")
    if not image_b64:
        return error("图像数据不能为空", 400)
    try:
        image_bytes = base64.b64decode(image_b64.split(",")[-1])
    except Exception:
        return error("图像数据格式错误", 400)
    result = _svc.process_frame(task_id, image_bytes)
    if result["ok"]:
        return success(result["data"])
    return error(result["message"], result["code"])


# ── 考勤记录 ──────────────────────────────────────────────────────

@bp.get("/records")
@require_auth
def list_records():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    filters = {
        "task_id": request.args.get("task_id"),
        "course_id": request.args.get("course_id"),
        "status": request.args.get("status"),
        "date_from": request.args.get("date_from"),
        "date_to": request.args.get("date_to"),
    }
    # 学生角色只能查自己
    if g.current_role == "student":
        filters["current_user_id"] = g.current_user_id
    result = _svc.get_records(page, per_page, filters)
    return paginated(result["items"], result["total"], page, per_page)


@bp.put("/records/<int:record_id>")
@require_roles("admin", "teacher")
def update_record(record_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    note = data.get("note")
    if status not in ("present", "absent", "unverified"):
        return error("无效的考勤状态", 400)
    result = _svc.update_record(record_id, status, g.current_user_id, note)
    if result["ok"]:
        return success(result["data"])
    return error(result["message"], result["code"])
