"""AI 推理单例管理器（热加载特征库 + 统一推理入口）"""
from __future__ import annotations
import threading
import logging
import numpy as np
from typing import List, Optional

logger = logging.getLogger(__name__)


class ModelManager:
    _instance: Optional[ModelManager] = None
    _lock = threading.Lock()

    def __init__(self, config: dict):
        self.config = config
        self._model_lock = threading.RLock()

        from app.ai.face_detector import FaceDetector
        from app.ai.preprocessor import Preprocessor
        from app.ai.face_recognizer import FaceRecognizer
        from app.ai.feature_database import FeatureDatabase

        self.detector = FaceDetector(
            min_face_size=config.get("face_min_size", 40)
        )
        self.preprocessor = Preprocessor()
        self.feature_db = FeatureDatabase()

        weights_path, num_classes = self._find_latest_weights(config)
        try:
            self.recognizer = FaceRecognizer(
                model_type=config.get("model_type", "resnet50"),
                weights_path=weights_path,
                device=config.get("device", "cpu"),
                num_classes=num_classes,
            )
            logger.info("FaceRecognizer loaded (model=%s, weights=%s, classes=%d)",
                        config.get("model_type"), weights_path, num_classes)
        except Exception as e:
            logger.warning("FaceRecognizer init failed: %s — inference disabled", e)
            self.recognizer = None

        if config.get("feature_db_path"):
            try:
                self.feature_db.load(config["feature_db_path"])
                logger.info("FeatureDatabase loaded: %d students", len(self.feature_db))
            except Exception as e:
                logger.warning("FeatureDatabase load failed: %s", e)

    @classmethod
    def get_instance(cls, config: dict = None) -> ModelManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    if config is None:
                        raise RuntimeError(
                            "ModelManager not initialised — call get_instance(config) first"
                        )
                    cls._instance = ModelManager(config)
        return cls._instance

    @classmethod
    def reset(cls):
        """测试用：重置单例"""
        with cls._lock:
            cls._instance = None

    def reload_feature_db(self) -> None:
        path = self.config.get("feature_db_path")
        if not path:
            return
        from app.ai.feature_database import FeatureDatabase
        new_db = FeatureDatabase()
        new_db.load(path)
        with self._model_lock:
            self.feature_db = new_db
        logger.info("FeatureDatabase reloaded: %d students", len(new_db))

    def reload_recognizer(self) -> None:
        """训练完成后重新加载识别器（更新权重和 num_classes）"""
        from app.ai.face_recognizer import FaceRecognizer
        weights_path, num_classes = self._find_latest_weights(self.config)
        try:
            new_rec = FaceRecognizer(
                model_type=self.config.get("model_type", "resnet50"),
                weights_path=weights_path,
                device=self.config.get("device", "cpu"),
                num_classes=num_classes,
            )
            with self._model_lock:
                self.recognizer = new_rec
            logger.info("FaceRecognizer reloaded (classes=%d)", num_classes)
        except Exception as e:
            logger.error("FaceRecognizer reload failed: %s", e)

    def recognize_faces(self, image: np.ndarray) -> List[dict]:
        """
        端到端识别：BGR 图像 → [RecognitionResult, ...]
        每个 result 包含 status / student_id / student_db_id / confidence / bbox
        """
        if self.recognizer is None:
            return []
        bboxes = self.detector.detect(image)
        if not bboxes:
            return []
        results = []
        with self._model_lock:
            for bbox in bboxes:
                try:
                    tensor = self.preprocessor.preprocess(image, bbox)
                    feat = self.recognizer.extract_features(tensor)
                    match = self.feature_db.query(
                        feat,
                        threshold_high=self.config.get("similarity_threshold_high", 0.75),
                        threshold_low=self.config.get("similarity_threshold_low", 0.50),
                    )
                    match["bbox"] = [bbox.x1, bbox.y1, bbox.x2, bbox.y2]
                    results.append(match)
                except Exception as e:
                    logger.warning("Face recognition error for bbox %s: %s", bbox, e)
        return results

    def get_model_info(self) -> dict:
        return {
            "model_type": self.config.get("model_type"),
            "device": self.config.get("device"),
            "feature_db_size": len(self.feature_db),
            "recognizer_ready": self.recognizer is not None,
        }

    @staticmethod
    def _find_latest_weights(config: dict) -> tuple:
        """返回 (weights_path_or_None, num_classes)"""
        import os, glob, json
        ckpt_dir = config.get("checkpoint_dir", "")
        model_type = config.get("model_type", "resnet50")
        pattern = os.path.join(ckpt_dir, f"{model_type}_*.pth")
        files = sorted(glob.glob(pattern))
        weights_path = files[-1] if files else None

        num_classes = 2  # 缺省占位（strict=False 加载时分类头权重会被忽略）
        if weights_path:
            meta_path = os.path.join(ckpt_dir, f"{model_type}_meta.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path) as f:
                        num_classes = json.load(f).get("num_classes", 2)
                except Exception:
                    pass
        return weights_path, num_classes
