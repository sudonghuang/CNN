"""Gunicorn/eventlet 生产入口

启动命令（单进程 + eventlet worker，支持 WebSocket）：
  gunicorn -k eventlet -w 1 --worker-connections 1000 -b 0.0.0.0:5000 wsgi:app

注意：Flask-SocketIO + eventlet 不支持多 gunicorn worker，需配合 Redis 消息队列
才能横向扩展。开发阶段使用 run.py 的 socketio.run() 即可。
"""
import os

# 只在 gunicorn 工作进程（非 flask CLI）中做 monkey_patch
# gunicorn 会设置 SERVER_SOFTWARE 或者可以检测 gunicorn 模块是否已加载
_running_in_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "") or \
                       any("gunicorn" in mod for mod in __import__("sys").modules)

if _running_in_gunicorn:
    import eventlet
    eventlet.monkey_patch()

from app import create_app  # noqa: E402

app = create_app("production")
