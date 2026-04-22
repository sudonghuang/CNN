"""CNN 特征提取器（VGG16 / ResNet50）

推理架构与 model/train.py build_model 保持一致：
  VGG16   : features → GAP(1×1) → flatten → classifier[0-1] → 512-dim
  ResNet50: backbone → flatten  → fc[0-1]                   → 512-dim
"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List


class _VGG16Embedder(nn.Module):
    """VGG16 推理包装：forward 在 512-dim embedding 处截断（去掉最终分类层）"""

    def __init__(self, base: nn.Module):
        super().__init__()
        self.features = base.features
        self.avgpool = base.avgpool
        self.classifier = base.classifier  # 与 train.py build_model 完全相同的 Sequential

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)          # GAP → (B, 512, 1, 1)
        x = torch.flatten(x, 1)      # → (B, 512)
        # GAP后 classifier: [0]L(512,512) [1]ReLU [2]Dropout [3]L(512,C)
        # 取前 2 层（index 0-1）→ 512-dim embedding
        for layer in list(self.classifier.children())[:2]:
            x = layer(x)
        return x


class _ResNet50Embedder(nn.Module):
    """ResNet50 推理包装：forward 在 512-dim embedding 处截断"""

    def __init__(self, base: nn.Module):
        super().__init__()
        for name in ("conv1", "bn1", "relu", "maxpool",
                     "layer1", "layer2", "layer3", "layer4",
                     "avgpool", "fc"):
            setattr(self, name, getattr(base, name))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        # fc: [0]L(2048,512) [1]ReLU [2]Dropout [3]L(512,C)
        # 取前 2 层（index 0-1）→ 512-dim
        for layer in list(self.fc.children())[:2]:
            x = layer(x)
        return x


class FaceRecognizer:
    """加载预训练 CNN，输出 L2 归一化 512-dim 特征向量"""

    SUPPORTED = ("vgg16", "resnet50")

    def __init__(self, model_type: str, weights_path: str = None,
                 device: str = "cpu", num_classes: int = 2):
        if model_type not in self.SUPPORTED:
            raise ValueError(f"model_type must be one of {self.SUPPORTED}")
        self.model_type = model_type
        self.device = torch.device(device)
        if weights_path:
            state = torch.load(weights_path, map_location=self.device,
                               weights_only=True)
            # Auto-detect num_classes from checkpoint to avoid shape mismatch
            num_classes = self._detect_num_classes(state, model_type, num_classes)
        else:
            state = None
        self.model = self._build_model(model_type, num_classes)
        if state is not None:
            self.model.load_state_dict(state, strict=False)
        self.model.to(self.device)
        self.model.eval()

    @staticmethod
    def _detect_num_classes(state_dict: dict, model_type: str, default: int) -> int:
        """从 state_dict 中读取分类层权重形状，推断 num_classes"""
        key = "classifier.3.weight" if model_type == "vgg16" else "fc.3.weight"
        if key in state_dict:
            return int(state_dict[key].shape[0])
        return default

    def _build_model(self, model_type: str, num_classes: int) -> nn.Module:
        """构建与 train.py build_model 完全相同的分类头，再套上 Embedder 包装"""
        import torchvision.models as tvm
        if model_type == "vgg16":
            base = tvm.vgg16(weights=None)
            base.avgpool = nn.AdaptiveAvgPool2d((1, 1))   # GAP
            base.classifier = nn.Sequential(
                nn.Linear(512, 512), nn.ReLU(True), nn.Dropout(0.4),
                nn.Linear(512, num_classes),
            )
            return _VGG16Embedder(base)
        else:  # resnet50
            base = tvm.resnet50(weights=None)
            base.fc = nn.Sequential(
                nn.Linear(2048, 512), nn.ReLU(True), nn.Dropout(0.3),
                nn.Linear(512, num_classes),
            )
            return _ResNet50Embedder(base)

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
