"""开发服务器启动入口"""
import torch
torch.set_num_threads(2)   # 限制 PyTorch CPU 线程数，减少内存碎片

from app import create_app
from app.extensions import socketio

app = create_app("development")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)
