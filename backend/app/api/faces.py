"""人脸数据 Blueprint — /api/faces"""
import base64
from flask import Blueprint, request, current_app
from app.utils.response import success, error
from app.utils.auth import require_roles
from app.services.face_service import FaceService

bp = Blueprint("faces", __name__, url_prefix="/api/faces")
_svc = FaceService()


@bp.post("/<int:student_id>/upload")
@require_roles("admin")
def upload_faces(student_id):
    """批量上传人脸图片（multipart/form-data）"""
    files = request.files.getlist("images")
    if not files:
        return error("请选择图片文件", 400)
    results = []
    for f in files:
        if not f.filename.lower().endswith((".jpg", ".jpeg", ".png")):
            results.append({"filename": f.filename, "ok": False, "msg": "不支持的格式"})
            continue
        r = _svc.upload_and_preprocess(student_id, f)
        results.append({"filename": f.filename, **r})
    return success(results)


@bp.post("/<int:student_id>/capture")
@require_roles("admin")
def capture_face(student_id):
    """摄像头截帧采集——前端传 base64 图像"""
    data = request.get_json(silent=True) or {}
    image_b64 = data.get("image")
    if not image_b64:
        return error("图像数据不能为空", 400)
    try:
        image_bytes = base64.b64decode(image_b64.split(",")[-1])
    except Exception:
        return error("图像数据格式错误", 400)
    result = _svc.capture_from_bytes(student_id, image_bytes)
    if result["ok"]:
        return success(result["data"])
    return error(result["message"], result["code"])


@bp.get("/<int:student_id>")
@require_roles("admin")
def list_faces(student_id):
    """获取某学生的人脸图片列表"""
    images = _svc.get_face_images(student_id)
    return success(images)


@bp.delete("/<int:image_id>")
@require_roles("admin")
def delete_face(image_id):
    result = _svc.delete_face_image(image_id)
    if result["ok"]:
        return success(None, "删除成功")
    return error(result["message"], result["code"])


@bp.post("/train")
@require_roles("admin")
def trigger_training():
    """手动触发模型训练（异步）"""
    data = request.get_json(silent=True) or {}
    model_type = data.get("model_type", current_app.config["AI_CONFIG"]["model_type"])
    result = _svc.trigger_training(model_type)
    if result["ok"]:
        return success({"job_id": result.get("job_id")}, "训练任务已提交")
    return error(result["message"], result["code"])
