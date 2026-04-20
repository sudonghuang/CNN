"""
迁移学习训练脚本（两阶段：先冻结主干微调头，再整体微调）
用法：python model/train.py --model resnet50 --epochs 30
"""
import os
import sys
import json
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

DATASET_ROOT   = os.path.join(os.path.dirname(__file__), "..", "dataset", "faces")
TRAIN_DIR      = os.path.join(DATASET_ROOT, "train")
VAL_DIR        = os.path.join(DATASET_ROOT, "val")
CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")
FEATURE_DB_PATH = os.path.join(os.path.dirname(__file__), "features.npy")


def get_transforms(is_train: bool):
    if is_train:
        return transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.RandomCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
            transforms.RandomRotation(15),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


def build_model(model_type: str, num_classes: int, pretrained: bool = True):
    """构建分类模型（与 face_recognizer.py 保持架构一致）"""
    if model_type == "vgg16":
        weights = models.VGG16_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.vgg16(weights=weights)
        model.classifier = nn.Sequential(
            nn.Linear(25088, 4096), nn.ReLU(True), nn.Dropout(0.5),
            nn.Linear(4096, 512),   nn.ReLU(True), nn.Dropout(0.5),
            nn.Linear(512, num_classes),
        )
    elif model_type == "resnet50":
        weights = models.ResNet50_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.resnet50(weights=weights)
        model.fc = nn.Sequential(
            nn.Linear(2048, 512), nn.ReLU(True), nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )
    else:
        raise ValueError(f"Unsupported model: {model_type}")
    return model


def _freeze_backbone(model, model_type: str):
    """冻结主干卷积层，只训练分类头"""
    if model_type == "vgg16":
        for p in model.features.parameters():
            p.requires_grad = False
    else:
        for name, p in model.named_parameters():
            if not name.startswith("fc"):
                p.requires_grad = False


def _unfreeze_all(model):
    """解冻所有参数，用于第二阶段整体微调"""
    for p in model.parameters():
        p.requires_grad = True


def _forward_embedding(model, model_type: str, x: torch.Tensor) -> torch.Tensor:
    """
    用训练好的模型提取 512-dim embedding（不含最终分类层）。
    与 face_recognizer.py 中 Embedder 的 forward 逻辑保持一致。
    """
    if model_type == "vgg16":
        h = model.features(x)
        h = model.avgpool(h)
        h = torch.flatten(h, 1)
        # classifier: [0]L(25088,4096) [1]ReLU [2]Dropout
        #             [3]L(4096,512)   [4]ReLU [5]Dropout [6]L(512,C)
        for layer in list(model.classifier.children())[:5]:
            h = layer(h)
    else:  # resnet50
        h = model.conv1(x); h = model.bn1(h); h = model.relu(h)
        h = model.maxpool(h)
        h = model.layer1(h); h = model.layer2(h)
        h = model.layer3(h); h = model.layer4(h)
        h = model.avgpool(h)
        h = torch.flatten(h, 1)
        # fc: [0]L(2048,512) [1]ReLU [2]Dropout [3]L(512,C)
        for layer in list(model.fc.children())[:2]:
            h = layer(h)
    return h


def _eval_epoch(model, loader, device):
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for imgs, labels in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            preds = model(imgs).argmax(1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    return correct / total if total else 0.0


def run_training(model_type: str = "resnet50", epochs: int = 30,
                 batch_size: int = 32, lr: float = 1e-4) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training %s on %s", model_type, device)

    # 优先使用 prepare_lfw.py 划分好的 train/val 子目录，否则回退到旧的随机 split
    if os.path.isdir(TRAIN_DIR) and os.path.isdir(VAL_DIR):
        train_ds = datasets.ImageFolder(TRAIN_DIR, transform=get_transforms(True))
        val_ds   = datasets.ImageFolder(VAL_DIR,   transform=get_transforms(False))
        # 合并 full_ds 用于训练后提取特征库（兼容 _extract_feature_db）
        full_ds  = datasets.ImageFolder(TRAIN_DIR, transform=get_transforms(False))
    else:
        full_ds = datasets.ImageFolder(DATASET_ROOT, transform=get_transforms(True))
        if len(full_ds.classes) == 0:
            logger.error("No classes found in %s", DATASET_ROOT)
            return {"error": "no data"}
        n = len(full_ds)
        n_val = max(1, int(n * 0.2))
        train_ds, val_ds = torch.utils.data.random_split(
            full_ds, [n - n_val, n_val],
            generator=torch.Generator().manual_seed(42),
        )
        val_ds.dataset.transform = get_transforms(False)

    if len(train_ds) == 0:
        logger.error("Train set is empty, check %s", TRAIN_DIR)
        return {"error": "no data"}

    # CPU 训练：num_workers=0 避免进程间通信开销，pin_memory 仅对 GPU 有效
    use_workers = 0 if not torch.cuda.is_available() else 2
    train_loader = DataLoader(train_ds, batch_size=batch_size,
                              shuffle=True,  num_workers=use_workers)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size,
                              shuffle=False, num_workers=use_workers)
    num_classes = len(train_ds.classes) if hasattr(train_ds, "classes") else len(full_ds.classes)
    logger.info("Classes: %d  Train: %d  Val: %d", num_classes, len(train_ds), len(val_ds))

    model = build_model(model_type, num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    # ── 阶段一：冻结主干，仅训练分类头（前 1/3 轮） ───────────────────
    # Phase 1 用较高固定 LR（不衰减），让分类头在 ImageNet 特征上快速收敛
    # 不使用 StepLR：避免 LR 在 phase 1 结束时降到 1e-6 导致学习停滞
    freeze_epochs = max(1, epochs // 3)
    _freeze_backbone(model, model_type)
    head_params = [p for p in model.parameters() if p.requires_grad]
    phase1_lr = max(lr * 10, 1e-3)   # phase 1 用更高 LR：1e-3
    optimizer = optim.Adam(head_params, lr=phase1_lr)
    scheduler = None
    logger.info("Phase 1: freeze backbone, train head for %d epochs (lr=%.2e)",
                freeze_epochs, phase1_lr)

    best_acc, best_epoch = 0.0, 0

    for epoch in range(1, epochs + 1):
        # 阶段切换：第二阶段解冻所有层，使用较小 LR 防止破坏预训练特征
        if epoch == freeze_epochs + 1:
            _unfreeze_all(model)
            # Phase 2 用 SGD+momentum 替代 Adam：内存占用约 1/3，稳定微调
            optimizer = optim.SGD(model.parameters(), lr=lr,
                                  momentum=0.9, weight_decay=1e-4)
            scheduler = optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=epochs - freeze_epochs, eta_min=1e-6)
            logger.info("Phase 2: unfreeze all layers, SGD fine-tune (lr=%.2e)", lr)

        model.train()
        correct, total, running_loss = 0, 0, 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            correct += (out.argmax(1) == labels).sum().item()
            total += labels.size(0)

        train_acc = correct / total
        val_acc = _eval_epoch(model, val_loader, device)
        if scheduler is not None:
            scheduler.step()
        logger.info("Epoch %d/%d  loss=%.4f  train_acc=%.4f  val_acc=%.4f",
                    epoch, epochs, running_loss / len(train_loader), train_acc, val_acc)

        if val_acc > best_acc:
            best_acc = val_acc
            best_epoch = epoch
            ckpt = os.path.join(CHECKPOINT_DIR, f"{model_type}_best.pth")
            torch.save(model.state_dict(), ckpt)
            logger.info("Saved best checkpoint: %s (val_acc=%.4f)", ckpt, best_acc)

    # 保存元信息（供 ModelManager 读取 num_classes）
    meta = {"num_classes": num_classes, "best_acc": best_acc, "best_epoch": best_epoch,
            "model_type": model_type}
    meta_path = os.path.join(CHECKPOINT_DIR, f"{model_type}_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info("Saved meta: %s", meta_path)

    # 训练结束后释放内存，再在独立函数中提取特征库，避免 OOM
    del optimizer, train_loader, val_loader
    import gc; gc.collect()
    best_ckpt = os.path.join(CHECKPOINT_DIR, f"{model_type}_best.pth")
    model.load_state_dict(torch.load(best_ckpt, map_location=device, weights_only=True))
    _extract_feature_db(model, model_type, full_ds, device)
    return {"best_acc": best_acc, "best_epoch": best_epoch, "num_classes": num_classes}


def _extract_feature_db(model, model_type: str, dataset, device):
    """
    用训练好的模型为所有学生提取平均特征向量，保存至 features.npy。
    文件夹名即 student_id 字符串；db_id 通过查询数据库获得，查不到则置 -1。
    """
    import numpy as np
    from collections import defaultdict

    model.eval()
    loader = DataLoader(dataset, batch_size=8, shuffle=False, num_workers=0)
    class_to_feats: dict = defaultdict(list)

    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            feats = _forward_embedding(model, model_type, imgs)
            feats = torch.nn.functional.normalize(feats, p=2, dim=1)
            for f, l in zip(feats.cpu().numpy(), labels.numpy()):
                class_to_feats[int(l)].append(f)

    idx_to_class = {v: k for k, v in dataset.class_to_idx.items()}

    # 尝试从数据库获取 db_id（需在 Flask 应用上下文中运行）
    student_id_to_db_id: dict = {}
    try:
        from app.models.student import Student
        from app.extensions import db
        rows = db.session.query(Student.student_id, Student.id).all()
        student_id_to_db_id = {r.student_id: r.id for r in rows}
    except Exception as e:
        logger.warning("DB lookup skipped: %s", e)

    student_ids, db_ids, feature_matrix = [], [], []
    for class_idx, feats in class_to_feats.items():
        avg = np.mean(feats, axis=0)
        avg = avg / (np.linalg.norm(avg) + 1e-8)
        sid = idx_to_class[class_idx]          # 学号字符串（文件夹名）
        did = student_id_to_db_id.get(sid, -1) # 数据库 id
        student_ids.append(sid)
        db_ids.append(did)
        feature_matrix.append(avg)

    if feature_matrix:
        np.save(FEATURE_DB_PATH, {
            "student_ids": student_ids,
            "db_ids": db_ids,
            "feature_matrix": np.array(feature_matrix),
        })
        logger.info("Feature DB saved: %d students → %s", len(student_ids), FEATURE_DB_PATH)
    else:
        logger.warning("No features extracted — feature DB not updated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",      default="resnet50", choices=["vgg16", "resnet50"])
    parser.add_argument("--epochs",     type=int,   default=30)
    parser.add_argument("--batch-size", type=int,   default=16)
    parser.add_argument("--lr",         type=float, default=1e-4)
    args = parser.parse_args()
    result = run_training(args.model, args.epochs, args.batch_size, args.lr)
    logger.info("Training complete: %s", result)
