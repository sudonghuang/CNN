"""WebSocket 事件处理器（Flask-SocketIO）

协议约定（与前端 stores/attendance.js 对应）：
  客户端 → 服务端：
    connect   query: token=<JWT>
    join_task { task_id }
    frame     { task_id, image }   base64 JPEG，可含 data:image/... 前缀
    leave_task {}

  服务端 → 客户端（emit 到同一 task_id 房间）：
    recognition_result  { task_id, results: [...] }
    task_update         { task_id, status, present_count, total_students }
    error               { message }
"""
import base64
import logging
from flask import request, current_app
from flask_socketio import emit, join_room, leave_room, disconnect

from app.extensions import socketio, db
from app.services.attendance_service import AttendanceService

logger = logging.getLogger(__name__)
_svc = AttendanceService()


# ── 连接 / 断开 ─────────────────────────────────────────────────────

@socketio.on("connect")
def handle_connect():
    """验证 JWT token（query 参数或 Authorization header）"""
    token = request.args.get("token") or (
        request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )
    if not token:
        logger.warning("WS connect rejected: no token")
        return False  # 拒绝连接

    try:
        from flask_jwt_extended import decode_token
        decoded = decode_token(token)
        request.ws_user_id = int(decoded["sub"])
        request.ws_role = decoded.get("role", "student")
    except Exception as e:
        logger.warning("WS connect rejected: invalid token (%s)", e)
        return False

    logger.info("WS connected: user=%s sid=%s", request.ws_user_id, request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    logger.info("WS disconnected: sid=%s", request.sid)


# ── 加入 / 离开考勤房间 ─────────────────────────────────────────────

@socketio.on("join_task")
def handle_join_task(data):
    """加入指定考勤任务的 SocketIO 房间"""
    task_id = data.get("task_id")
    if not task_id:
        emit("error", {"message": "task_id 不能为空"})
        return
    room = f"task_{task_id}"
    join_room(room)
    logger.debug("sid=%s joined room=%s", request.sid, room)


@socketio.on("leave_task")
def handle_leave_task(data):
    task_id = data.get("task_id")
    if task_id:
        leave_room(f"task_{task_id}")


# ── 视频帧识别 ────────────────────────────────────────────────────────

@socketio.on("frame")
def handle_frame(data):
    """接收一帧 base64 图像，调用 AI 识别，广播识别结果到同房间"""
    task_id = data.get("task_id")
    image_b64 = data.get("image", "")

    if not task_id or not image_b64:
        emit("error", {"message": "task_id 和 image 不能为空"})
        return

    # 剥离 data URI 前缀（如 "data:image/jpeg;base64,..."）
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        emit("error", {"message": "图像 base64 解码失败"})
        return

    # 使用 Flask 应用上下文（SocketIO eventlet 模式已自动 push context）
    result = _svc.process_frame(task_id, image_bytes)
    if not result["ok"]:
        emit("error", {"message": result["message"]})
        return

    results = result["data"]
    if results:
        # 广播识别结果给同一房间所有客户端（包含发送方）
        socketio.emit(
            "recognition_result",
            {"task_id": task_id, "results": results},
            room=f"task_{task_id}",
        )

        # 同步推送任务最新统计（present_count / total_students）
        _push_task_update(task_id)


def _push_task_update(task_id: int):
    """向房间广播任务出勤统计快照（SocketIO 事件处理器内部已有 app context）"""
    try:
        from app.models.attendance import AttendanceTask
        task = db.session.get(AttendanceTask, task_id)
        if task:
            socketio.emit(
                "task_update",
                {
                    "task_id": task_id,
                    "status": task.status,
                    "present_count": task.present_count or 0,
                    "total_students": task.total_students or 0,
                },
                room=f"task_{task_id}",
            )
    except Exception as e:
        logger.error("Failed to push task_update: %s", e)
