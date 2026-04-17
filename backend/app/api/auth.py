"""认证 Blueprint — /api/auth"""
from flask import Blueprint, request
from flask_jwt_extended import create_access_token, get_jwt_identity
from app.utils.response import success, error
from app.utils.auth import require_auth
from app.services.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
_svc = AuthService()


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return error("账号和密码不能为空", 400)
    result = _svc.login(username, password)
    if result["ok"]:
        return success(result["data"])
    return error(result["message"], result["code"])


@bp.post("/logout")
@require_auth
def logout():
    # JWT 无状态，客户端删除 Token 即可；服务端可维护黑名单（P2）
    return success(None, "已退出登录")


@bp.put("/password")
@require_auth
def change_password():
    data = request.get_json(silent=True) or {}
    old_pw = data.get("old_password") or ""
    new_pw = data.get("new_password") or ""
    if not old_pw or not new_pw:
        return error("请填写旧密码和新密码", 400)
    if len(new_pw) < 6:
        return error("新密码不能少于6位", 400)
    from flask import g
    result = _svc.change_password(g.current_user_id, old_pw, new_pw)
    if result["ok"]:
        return success(None, "密码修改成功")
    return error(result["message"], result["code"])
