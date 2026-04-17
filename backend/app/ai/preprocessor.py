"""人脸图像预处理（裁剪 → Resize → 归一化 → Tensor）"""
import cv2
import numpy as np
import torch
from torchvision import transforms

from app.ai.face_detector import BoundingBox

# ImageNet 均值/标准差
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD  = [0.229, 0.224, 0.225]


class Preprocessor:
    def __init__(self, target_size: tuple = (224, 224)):
        self.target_size = target_size
        self._transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
        ])

    def crop_face(self, image: np.ndarray, bbox: BoundingBox,
                  padding: int = 20) -> np.ndarray:
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox.to_crop_coords(padding, img_h=h, img_w=w)
        return image[y1:y2, x1:x2]

    def resize(self, image: np.ndarray) -> np.ndarray:
        return cv2.resize(image, self.target_size, interpolation=cv2.INTER_LINEAR)

    def to_tensor(self, image: np.ndarray) -> torch.Tensor:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return self._transform(rgb)

    def preprocess(self, image: np.ndarray, bbox: BoundingBox) -> torch.Tensor:
        """完整预处理流水线，返回形状 (3, H, W) 的 Tensor"""
        face = self.crop_face(image, bbox)
        face = self.resize(face)
        return self.to_tensor(face)
