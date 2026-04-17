"""统一 HTTP 响应格式"""
import uuid
from flask import jsonify


def success(data=None, message="success", code=200):
    return jsonify({
        "code": code,
        "message": message,
        "data": data,
        "request_id": str(uuid.uuid4())[:8],
    }), code


def error(message: str, code=400, data=None):
    return jsonify({
        "code": code,
        "message": message,
        "data": data,
        "request_id": str(uuid.uuid4())[:8],
    }), code


def paginated(items: list, total: int, page: int, per_page: int):
    return success({
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }
    })
