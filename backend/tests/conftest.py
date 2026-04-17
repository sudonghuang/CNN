"""
pytest 全局 fixtures

使用 SQLite in-memory 数据库，无需启动 MySQL 即可运行单元/集成测试。
"""
import os
import pytest

# 在 import Flask app 之前设置测试环境变量
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "sqlite:///:memory:",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")


@pytest.fixture(scope="session")
def app():
    """创建一次性 Flask 应用（整个测试 session 共用）"""
    from app import create_app
    application = create_app("testing")
    application.config["TESTING"] = True
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    application.config["WTF_CSRF_ENABLED"] = False
    yield application


@pytest.fixture(scope="session")
def _db(app):
    """Session 级别：创建所有表，测试结束后 drop"""
    from app.extensions import db
    with app.app_context():
        db.create_all()
        yield db
        db.drop_all()


@pytest.fixture(scope="function")
def db_session(_db, app):
    """Function 级别：每个测试在事务中运行，测试后回滚"""
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()
        _db.session.bind = connection  # type: ignore
        yield _db.session
        _db.session.remove()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(app, _db):
    """Flask 测试客户端（每个测试函数独立）"""
    with app.app_context():
        _db.create_all()
        yield app.test_client()
        _db.session.remove()
        _db.drop_all()
        _db.create_all()


@pytest.fixture
def admin_user(client, app):
    """创建管理员用户并返回 JWT token"""
    from app.extensions import db
    from app.models.user import User
    with app.app_context():
        u = User(username="admin_test", role="admin", real_name="测试管理员")
        u.set_password("Test@123456")
        db.session.add(u)
        db.session.commit()
        uid = u.id

    resp = client.post("/api/auth/login", json={
        "username": "admin_test", "password": "Test@123456"
    })
    token = resp.get_json()["data"]["token"]
    return {"token": token, "user_id": uid}


@pytest.fixture
def teacher_user(client, app):
    """创建教师用户并返回 JWT token"""
    from app.extensions import db
    from app.models.user import User
    with app.app_context():
        u = User(username="teacher_test", role="teacher", real_name="测试教师")
        u.set_password("Test@123456")
        db.session.add(u)
        db.session.commit()

    resp = client.post("/api/auth/login", json={
        "username": "teacher_test", "password": "Test@123456"
    })
    token = resp.get_json()["data"]["token"]
    return {"token": token}


def auth_header(token: str) -> dict:
    """生成带 JWT 的请求头"""
    return {"Authorization": f"Bearer {token}"}
