"""用户管理 Blueprint — /api/users（仅管理员可访问）"""
from flask import Blueprint, request, g
from app.extensions import db
from app.models.user import User
from app.utils.response import success, error, paginated
from app.utils.auth import require_roles, require_auth

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.get("")
@require_roles("admin")
def list_users():
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    q = User.query
    if request.args.get("role"):
        q = q.filter_by(role=request.args["role"])
    if request.args.get("keyword"):
        kw = f"%{request.args['keyword']}%"
        q = q.filter(
            db.or_(User.username.ilike(kw), User.real_name.ilike(kw))
        )
    pagination = q.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return paginated([u.to_dict() for u in pagination.items],
                     pagination.total, page, per_page)


@bp.post("")
@require_roles("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    required = ["username", "password", "role", "real_name"]
    for f in required:
        if not data.get(f):
            return error(f"{f} 不能为空", 400)
    allowed_roles = ("admin", "teacher", "counselor", "student")
    if data["role"] not in allowed_roles:
        return error(f"角色必须是 {allowed_roles} 之一", 400)
    if len(data["password"]) < 6:
        return error("密码不能少于6位", 400)
    if User.query.filter_by(username=data["username"]).first():
        return error("用户名已存在", 409)
    user = User(
        username=data["username"].strip(),
        role=data["role"],
        real_name=data["real_name"].strip(),
        email=data.get("email", "").strip() or None,
        is_active=True,
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return success(user.to_dict(), code=201)


@bp.get("/<int:user_id>")
@require_roles("admin")
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return error("用户不存在", 404)
    return success(user.to_dict())


@bp.put("/<int:user_id>")
@require_roles("admin")
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return error("用户不存在", 404)
    data = request.get_json(silent=True) or {}
    for field in ("real_name", "email"):
        if data.get(field) is not None:
            setattr(user, field, data[field].strip() or None)
    if data.get("role"):
        allowed_roles = ("admin", "teacher", "counselor", "student")
        if data["role"] not in allowed_roles:
            return error(f"角色必须是 {allowed_roles} 之一", 400)
        user.role = data["role"]
    if data.get("password"):
        if len(data["password"]) < 6:
            return error("密码不能少于6位", 400)
        user.set_password(data["password"])
    db.session.commit()
    return success(user.to_dict())


@bp.delete("/<int:user_id>")
@require_roles("admin")
def delete_user(user_id):
    if user_id == g.current_user_id:
        return error("不能删除当前登录账号", 400)
    user = User.query.get(user_id)
    if not user:
        return error("用户不存在", 404)
    db.session.delete(user)
    db.session.commit()
    return success({"id": user_id})


@bp.put("/<int:user_id>/active")
@require_roles("admin")
def toggle_active(user_id):
    """启用/禁用用户账号"""
    if user_id == g.current_user_id:
        return error("不能禁用当前登录账号", 400)
    user = User.query.get(user_id)
    if not user:
        return error("用户不存在", 404)
    data = request.get_json(silent=True) or {}
    user.is_active = bool(data.get("is_active", not user.is_active))
    db.session.commit()
    return success(user.to_dict())


@bp.get("/me")
@require_auth
def get_me():
    """获取当前登录用户信息"""
    user = User.query.get(g.current_user_id)
    if not user:
        return error("用户不存在", 404)
    return success(user.to_dict())
