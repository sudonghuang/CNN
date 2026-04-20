"""人脸数据业务逻辑"""
import os
import uuid
import threading
from datetime import datetime
from flask import current_app
from app.extensions import db
from app.models.student import Student, FaceImage

# 进程级训练任务状态表（key: job_id）
_training_jobs: dict = {}
_jobs_lock = threading.Lock()


class FaceService:
    def _save_bytes_to_disk(self, student_db_id: int, image_bytes: bytes,
                            suffix: str = ".jpg") -> str:
        upload_dir = os.path.join(
            current_app.config["UPLOAD_FOLDER"], str(student_db_id)
        )
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{suffix}"
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return filepath

    def upload_and_preprocess(self, student_db_id: int, file_storage) -> dict:
        student = Student.query.get(student_db_id)
        if not student:
            return {"ok": False, "code": 404, "message": "学生不存在"}
        suffix = os.path.splitext(file_storage.filename)[1].lower() or ".jpg"
        image_bytes = file_storage.read()
        filepath = self._save_bytes_to_disk(student_db_id, image_bytes, suffix)
        return self._register_image(student, filepath)

    def capture_from_bytes(self, student_db_id: int, image_bytes: bytes) -> dict:
        student = Student.query.get(student_db_id)
        if not student:
            return {"ok": False, "code": 404, "message": "学生不存在"}
        filepath = self._save_bytes_to_disk(student_db_id, image_bytes, ".jpg")
        return self._register_image(student, filepath)

    def _register_image(self, student: Student, filepath: str) -> dict:
        """检测人脸 → 写库 → 更新 face_count"""
        try:
            from app.ai.model_manager import ModelManager
            import cv2
            img = cv2.imread(filepath)
            if img is None:
                os.remove(filepath)
                return {"ok": False, "code": 422, "message": "图片读取失败"}
            bboxes = ModelManager.get_instance().detector.detect(img)
            if not bboxes:
                os.remove(filepath)
                return {"ok": False, "code": 422, "message": "未检测到人脸，请上传正面清晰照片"}
        except Exception as e:
            current_app.logger.warning("Face detection skipped: %s", e)

        face_img = FaceImage(student_id=student.id, file_path=filepath,
                             is_processed=True)
        db.session.add(face_img)
        student.face_count += 1
        if student.face_count >= current_app.config["FACE_MIN_COUNT"]:
            student.face_registered = True
        db.session.commit()
        return {"ok": True, "data": face_img.to_dict()}

    def get_face_images(self, student_db_id: int) -> list:
        imgs = FaceImage.query.filter_by(student_id=student_db_id).order_by(
            FaceImage.created_at
        ).all()
        return [i.to_dict() for i in imgs]

    def delete_face_image(self, image_id: int) -> dict:
        img = FaceImage.query.get(image_id)
        if not img:
            return {"ok": False, "code": 404, "message": "图片不存在"}
        try:
            if os.path.exists(img.file_path):
                os.remove(img.file_path)
        except OSError:
            pass
        student = Student.query.get(img.student_id)
        if student and student.face_count > 0:
            student.face_count -= 1
            if student.face_count < current_app.config["FACE_MIN_COUNT"]:
                student.face_registered = False
        db.session.delete(img)
        db.session.commit()
        return {"ok": True}

    # ── 模型训练 ─────────────────────────────────────────────────

    def trigger_training(self, model_type: str) -> dict:
        job_id = uuid.uuid4().hex[:8]
        with _jobs_lock:
            _training_jobs[job_id] = {
                "status": "running",
                "model_type": model_type,
                "started_at": datetime.now().isoformat(),
                "finished_at": None,
                "result": None,
                "error": None,
            }
        t = threading.Thread(
            target=self._run_training,
            args=(model_type, job_id, current_app._get_current_object()),
            daemon=True,
        )
        t.start()
        return {"ok": True, "job_id": job_id}

    def _run_training(self, model_type: str, job_id: str, app) -> None:
        with app.app_context():
            try:
                from model.train import run_training
                result = run_training(model_type)
                from app.ai.model_manager import ModelManager
                mgr = ModelManager.get_instance()
                mgr.reload_feature_db()
                mgr.reload_recognizer()
                with _jobs_lock:
                    _training_jobs[job_id].update({
                        "status": "done",
                        "finished_at": datetime.now().isoformat(),
                        "result": result,
                    })
                app.logger.info("Training job %s finished: %s", job_id, result)
            except Exception as e:
                with _jobs_lock:
                    _training_jobs[job_id].update({
                        "status": "failed",
                        "finished_at": datetime.now().isoformat(),
                        "error": str(e),
                    })
                app.logger.error("Training job %s failed: %s", job_id, e)

    def get_training_status(self, job_id: str) -> dict:
        job = _training_jobs.get(job_id)
        if job is None:
            return {"ok": False, "code": 404, "message": "训练任务不存在"}
        return {"ok": True, "data": {"job_id": job_id, **job}}

    def list_training_jobs(self) -> list:
        with _jobs_lock:
            return [{"job_id": k, **v} for k, v in _training_jobs.items()]
