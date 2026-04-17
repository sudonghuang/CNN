"""应用配置（开发/测试/生产三套）"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BaseConfig:
    # ── 基础 ──────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    JSON_AS_ASCII = False

    # ── 数据库 ────────────────────────────────────────
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300}

    # ── JWT ───────────────────────────────────────────
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # ── 文件存储 ──────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "dataset", "faces")
    CHECKPOINT_DIR = os.path.join(BASE_DIR, "model", "checkpoints")
    FEATURE_DB_PATH = os.path.join(BASE_DIR, "model", "features.npy")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB

    # ── AI 推理 ───────────────────────────────────────
    AI_CONFIG = {
        "model_type": os.environ.get("MODEL_TYPE", "resnet50"),
        "device": os.environ.get("DEVICE", "cpu"),
        "similarity_threshold_high": float(os.environ.get("SIM_THRESHOLD_HIGH", "0.75")),
        "similarity_threshold_low": float(os.environ.get("SIM_THRESHOLD_LOW", "0.50")),
        "face_min_size": 40,
        "feature_db_path": os.path.join(BASE_DIR, "model", "features.npy"),
        "checkpoint_dir": os.path.join(BASE_DIR, "model", "checkpoints"),
    }

    # ── 业务参数 ──────────────────────────────────────
    FACE_MIN_COUNT = int(os.environ.get("FACE_MIN_COUNT", "5"))
    ABSENCE_TRIGGER_COUNT = int(os.environ.get("ABSENCE_TRIGGER_COUNT", "3"))
    TRAIN_TRIGGER_BATCH = int(os.environ.get("TRAIN_TRIGGER_BATCH", "10"))
    WS_FRAME_INTERVAL_MS = int(os.environ.get("WS_FRAME_INTERVAL_MS", "500"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DEV_DATABASE_URL",
        "mysql+pymysql://root:password@localhost:3306/attendance_dev?charset=utf8mb4",
    )
    SQLALCHEMY_ECHO = False  # True 会输出所有 SQL


class TestingConfig(BaseConfig):
    TESTING = True
    # 默认使用 SQLite 内存库，方便 CI 无 MySQL 环境下运行
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_ECHO = False


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
