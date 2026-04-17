"""MTCNN 人脸检测器"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import numpy as np


@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    landmarks: np.ndarray = field(default=None, repr=False)

    def to_crop_coords(self, padding: int = 20, img_h: int = 0, img_w: int = 0):
        x1 = max(0, self.x1 - padding)
        y1 = max(0, self.y1 - padding)
        x2 = min(img_w or self.x2 + padding, self.x2 + padding)
        y2 = min(img_h or self.y2 + padding, self.y2 + padding)
        return x1, y1, x2, y2


class FaceDetector:
    """MTCNN 多级联人脸检测器（首次调用时延迟加载模型）"""

    def __init__(self, min_face_size: int = 40,
                 thresholds: List[float] = None,
                 factor: float = 0.709):
        self.min_face_size = min_face_size
        self.thresholds = thresholds or [0.6, 0.7, 0.7]
        self.factor = factor
        self._mtcnn = None  # 延迟加载

    def _load(self):
        if self._mtcnn is None:
            from facenet_pytorch import MTCNN
            import torch
            device = "cuda" if __import__("torch").cuda.is_available() else "cpu"
            self._mtcnn = MTCNN(
                min_face_size=self.min_face_size,
                thresholds=self.thresholds,
                factor=self.factor,
                keep_all=True,
                device=device,
            )

    def detect(self, image: np.ndarray) -> List[BoundingBox]:
        """
        image: BGR ndarray (OpenCV 格式)
        返回按置信度降序排列的 BoundingBox 列表
        """
        self._load()
        import cv2
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(rgb)
        boxes, probs, landmarks = self._mtcnn.detect(pil_img, landmarks=True)
        if boxes is None:
            return []
        results = []
        for box, prob, lm in zip(boxes, probs, landmarks or [None] * len(boxes)):
            if prob < self.thresholds[2]:
                continue
            results.append(BoundingBox(
                x1=int(box[0]), y1=int(box[1]),
                x2=int(box[2]), y2=int(box[3]),
                confidence=float(prob),
                landmarks=lm,
            ))
        return sorted(results, key=lambda b: b.confidence, reverse=True)

    def detect_batch(self, images: List[np.ndarray]) -> List[List[BoundingBox]]:
        return [self.detect(img) for img in images]
