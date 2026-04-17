"""认证业务逻辑"""
from flask_jwt_extended import create_access_token
from app.extensions import db
from app.models.user import User


class AuthService:
    def login(self, username: str, password: str) -> dict:
        user = User.query.filter_by(username=username).first()
        if not user:
            return {"ok": False, "code": 401, "message": "账号或密码错误"}
        if not user.is_active:
            return {"ok": False, "code": 403, "message": "账号已被禁用，请联系管理员"}
        if not user.check_password(password):
            return {"ok": False, "code": 401, "message": "账号或密码错误"}
        token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role, "real_name": user.real_name},
        )
        return {
            "ok": True,
            "data": {"token": token, "user": user.to_dict()},
        }

    def change_password(self, user_id: int, old_pw: str, new_pw: str) -> dict:
        user = User.query.get(user_id)
        if not user:
            return {"ok": False, "code": 404, "message": "用户不存在"}
        if not user.check_password(old_pw):
            return {"ok": False, "code": 401, "message": "旧密码错误"}
        user.set_password(new_pw)
        db.session.commit()
        return {"ok": True}
