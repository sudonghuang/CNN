"""Flask 扩展单例——在 create_app() 中 init_app()"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from flask_socketio import SocketIO

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
migrate = Migrate()
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")
