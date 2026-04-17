"""Flask 应用工厂"""
import os
import logging
from flask import Flask
from app.config import config_map
from app.extensions import db, jwt, cors, migrate, socketio


def create_app(env: str = None) -> Flask:
    env = env or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_map[env])

    _init_logging(app)
    _init_extensions(app)
    _register_blueprints(app)
    _init_websocket(app)
    _init_ai(app)
    _register_error_handlers(app)

    return app


def _init_logging(app: Flask):
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _init_extensions(app: Flask):
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    migrate.init_app(app, db)
    socketio.init_app(app)
    with app.app_context():
        from app.models import (  # noqa: F401
            User, Student, StudentCourse, FaceImage,
            Course, AttendanceTask, AttendanceRecord,
        )


def _register_blueprints(app: Flask):
    from app.api import blueprints
    for bp in blueprints:
        app.register_blueprint(bp)


def _init_websocket(app: Flask):
    from app.ws import handlers  # noqa: F401 — registers @socketio.on handlers


def _init_ai(app: Flask):
    with app.app_context():
        try:
            from app.ai.model_manager import ModelManager
            ModelManager.get_instance(app.config["AI_CONFIG"])
        except Exception as e:
            app.logger.warning("AI module init skipped: %s", e)


def _register_error_handlers(app: Flask):
    from app.utils.response import error as err_resp
    from flask_jwt_extended.exceptions import NoAuthorizationError

    @app.errorhandler(400)
    def bad_request(e):
        return err_resp(str(e), 400)

    @app.errorhandler(403)
    def forbidden(e):
        return err_resp("权限不足", 403)

    @app.errorhandler(404)
    def not_found(e):
        return err_resp("资源不存在", 404)

    @app.errorhandler(413)
    def too_large(e):
        return err_resp("文件过大，请检查上传大小限制", 413)

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Internal server error")
        return err_resp("服务器内部错误，请联系管理员", 500)

    @app.errorhandler(NoAuthorizationError)
    def handle_no_auth(e):
        return err_resp("未提供认证 Token", 401)
