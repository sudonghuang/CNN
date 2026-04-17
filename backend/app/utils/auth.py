"""JWT 认证工具与角色权限装饰器"""
from functools import wraps
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from app.utils.response import error


def require_roles(*roles):
    """角色权限装饰器。用法：@require_roles('admin', 'teacher')"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") not in roles:
                return error("权限不足", 403)
            g.current_user_id = int(claims.get("sub"))
            g.current_role = claims.get("role")
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_auth(f):
    """仅验证登录，不限制角色"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        g.current_user_id = int(claims.get("sub"))
        g.current_role = claims.get("role")
        return f(*args, **kwargs)
    return wrapper
