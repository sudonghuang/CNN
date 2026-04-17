"""CNN 特征提取器（VGG16 / ResNet50）"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List


class FaceRecognizer:
    """加载预训练 CNN，去掉分类头，输出 L2 归一化特征向量"""

    SUPPORTED = ("vgg16", "resnet50")

    def __init__(self, model_type: str, weights_path: str = None,
                 device: str = "cpu"):
        if model_type not in self.SUPPORTED:
            raise ValueError(f"model_type must be one of {self.SUPPORTED}")
        self.model_type = model_type
        self.device = torch.device(device)
        self.model = self._build_model(model_type)
        if weights_path:
            state = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(state, strict=False)
        self.model.to(self.device)
        self.model.eval()

    def _build_model(self, model_type: str) -> nn.Module:
        import torchvision.models as tvm
        if model_type == "vgg16":
            base = tvm.vgg16(weights=None)
            # 去掉 classifier，只保留 features + avgpool
            backbone = nn.Sequential(
                base.features,
                base.avgpool,
                nn.Flatten(),
                nn.Linear(25088, 512),
                nn.BatchNorm1d(512),
                nn.ReLU(inplace=True),
            )
        else:  # resnet50
            base = tvm.resnet50(weights=None)
            base.fc = nn.Linear(2048, 512)
            backbone = base
        return backbone

    @torch.no_grad()
    def extract_features(self, face_tensor: torch.Tensor) -> np.ndarray:
        """face_tensor: (3, 224, 224) → ndarray (512,)"""
        x = face_tensor.unsqueeze(0).to(self.device)
        feat = self.model(x)
        feat = F.normalize(feat, p=2, dim=1)
        return feat.cpu().numpy().squeeze()

    @torch.no_grad()
    def extract_features_batch(self, tensors: List[torch.Tensor]) -> np.ndarray:
        """tensors: List[(3,224,224)] → ndarray (N, 512)"""
        batch = torch.stack(tensors).to(self.device)
        feats = self.model(batch)
        feats = F.normalize(feats, p=2, dim=1)
        return feats.cpu().numpy()
