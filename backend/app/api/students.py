"""学生管理 Blueprint — /api/students"""
from flask import Blueprint, request
from app.utils.response import success, error, paginated
from app.utils.auth import require_roles, require_auth
from app.services.student_service import StudentService

bp = Blueprint("students", __name__, url_prefix="/api/students")
_svc = StudentService()


@bp.get("")
@require_roles("admin", "teacher", "counselor")
def list_students():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    filters = {
        "name": request.args.get("name"),
        "class_name": request.args.get("class_name"),
        "face_registered": request.args.get("face_registered"),
    }
    result = _svc.get_students(page, per_page, filters)
    return paginated(result["items"], result["total"], page, per_page)


@bp.post("")
@require_roles("admin")
def create_student():
    data = request.get_json(silent=True) or {}
    result = _svc.create_student(data)
    if result["ok"]:
        return success(result["data"], code=201)
    return error(result["message"], result["code"])


@bp.get("/<int:student_id>")
@require_roles("admin", "teacher")
def get_student(student_id):
    result = _svc.get_student_by_id(student_id)
    if result:
        return success(result)
    return error("学生不存在", 404)


@bp.put("/<int:student_id>")
@require_roles("admin")
def update_student(student_id):
    data = request.get_json(silent=True) or {}
    result = _svc.update_student(student_id, data)
    if result["ok"]:
        return success(result["data"])
    return error(result["message"], result["code"])


@bp.delete("/<int:student_id>")
@require_roles("admin")
def delete_student(student_id):
    result = _svc.delete_student(student_id)
    if result["ok"]:
        return success(None, "删除成功")
    return error(result["message"], result["code"])


@bp.post("/import")
@require_roles("admin")
def import_students():
    if "file" not in request.files:
        return error("请上传 Excel 文件", 400)
    file = request.files["file"]
    if not file.filename.endswith((".xlsx", ".xls")):
        return error("仅支持 Excel 文件（.xlsx/.xls）", 400)
    result = _svc.import_from_excel(file)
    return success(result)


@bp.get("/classes")
@require_roles("admin", "teacher", "counselor")
def list_classes():
    """返回所有班级名称（用于下拉选择）"""
    result = _svc.get_all_classes()
    return success(result)
