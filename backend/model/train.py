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

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, WeightedRandomSampler
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
            transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.05),
            transforms.RandomGrayscale(p=0.1),
            transforms.RandomAffine(degrees=20, translate=(0.1, 0.1), scale=(0.9, 1.1)),
            transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            transforms.RandomErasing(p=0.2, scale=(0.02, 0.15), ratio=(0.3, 3.3)),
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
        # GAP：将 7×7 池化替换为全局平均池化，输出从 25088 降至 512
        # 分类头参数量：~26万（原 ~1.08亿），可使用 batch_size=32
        model.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        model.classifier = nn.Sequential(
            nn.Linear(512, 512), nn.ReLU(True), nn.Dropout(0.4),
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
        # GAP后 classifier: [0]L(512,512) [1]ReLU [2]Dropout [3]L(512,C)
        # 取前 2 层（index 0-1）→ 512-dim embedding
        for layer in list(model.classifier.children())[:2]:
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
                 batch_size: int = 32, lr: float = 1e-4,
                 resume: bool = False, grad_accum: int = 1) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training %s on %s  resume=%s  grad_accum=%d",
                model_type, device, resume, grad_accum)

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
    num_classes = len(train_ds.classes) if hasattr(train_ds, "classes") else len(full_ds.classes)
    logger.info("Classes: %d  Train: %d  Val: %d", num_classes, len(train_ds), len(val_ds))

    # 类别不平衡处理：计算每类样本数，构建加权随机采样器和加权损失
    targets = [s[1] for s in train_ds.imgs] if hasattr(train_ds, "imgs") else \
              [train_ds.dataset.targets[i] for i in train_ds.indices]
    class_counts = np.bincount(targets, minlength=num_classes).astype(np.float32)
    class_counts = np.maximum(class_counts, 1)
    sample_weights = 1.0 / class_counts[targets]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(targets), replacement=True)
    class_weights = torch.tensor(1.0 / class_counts, dtype=torch.float)
    logger.info("Class imbalance  max/min ratio=%.1f  WeightedSampler+WeightedLoss enabled",
                class_counts.max() / class_counts.min())

    train_loader = DataLoader(train_ds, batch_size=batch_size,
                              sampler=sampler, num_workers=use_workers)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size,
                              shuffle=False, num_workers=use_workers)

    model = build_model(model_type, num_classes, pretrained=not resume).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights.to(device))
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    # ── Resume 模式：从已有检查点继续 Phase 2 微调 ──────────────────────
    if resume:
        ckpt_path = os.path.join(CHECKPOINT_DIR, f"{model_type}_best.pth")
        if not os.path.exists(ckpt_path):
            logger.error("Resume requested but checkpoint not found: %s", ckpt_path)
            return {"error": "checkpoint not found"}
        model.load_state_dict(torch.load(ckpt_path, map_location=device, weights_only=True))

        # 读取已保存的最优指标，避免覆盖更好的历史结果
        meta_path = os.path.join(CHECKPOINT_DIR, f"{model_type}_meta.json")
        prev_best = 0.0
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                prev = json.load(f)
            prev_best = prev.get("best_acc", 0.0)

        # 先在验证集上测一下当前 checkpoint 的实际 val_acc
        cur_val = _eval_epoch(model, val_loader, device)
        best_acc  = max(prev_best, cur_val)
        best_epoch = 0
        logger.info("Resumed from %s  checkpoint_val_acc=%.4f  best_acc_so_far=%.4f",
                    ckpt_path, cur_val, best_acc)

        _unfreeze_all(model)
        optimizer = optim.SGD(model.parameters(), lr=lr, momentum=0.9, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=epochs, eta_min=1e-6)
        logger.info("Phase 2 (resume): SGD lr=%.2e, CosineAnnealing T_max=%d", lr, epochs)

        for epoch in range(1, epochs + 1):
            model.train()
            correct, total, running_loss = 0, 0, 0.0
            optimizer.zero_grad()
            for step, (imgs, labels) in enumerate(train_loader, 1):
                imgs, labels = imgs.to(device), labels.to(device)
                out  = model(imgs)
                loss = criterion(out, labels) / grad_accum
                loss.backward()
                running_loss += loss.item() * grad_accum
                correct += (out.argmax(1) == labels).sum().item()
                total   += labels.size(0)
                if step % grad_accum == 0 or step == len(train_loader):
                    optimizer.step()
                    optimizer.zero_grad()

            train_acc = correct / total
            val_acc   = _eval_epoch(model, val_loader, device)
            scheduler.step()
            cur_lr = optimizer.param_groups[0]["lr"]
            logger.info("Epoch %d/%d  lr=%.2e  loss=%.4f  train_acc=%.4f  val_acc=%.4f",
                        epoch, epochs, cur_lr,
                        running_loss / len(train_loader), train_acc, val_acc)

            if val_acc > best_acc:
                best_acc = val_acc
                best_epoch = epoch
                ckpt = os.path.join(CHECKPOINT_DIR, f"{model_type}_best.pth")
                torch.save(model.state_dict(), ckpt)
                logger.info("★ New best checkpoint: val_acc=%.4f", best_acc)

        meta = {"num_classes": num_classes, "best_acc": best_acc, "best_epoch": best_epoch,
                "model_type": model_type}
        with open(os.path.join(CHECKPOINT_DIR, f"{model_type}_meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        logger.info("Meta saved: %s", meta)

        del optimizer, train_loader, val_loader
        import gc; gc.collect()
        best_ckpt = os.path.join(CHECKPOINT_DIR, f"{model_type}_best.pth")
        model.load_state_dict(torch.load(best_ckpt, map_location=device, weights_only=True))
        _extract_feature_db(model, model_type, full_ds, device)
        return {"best_acc": best_acc, "best_epoch": best_epoch, "num_classes": num_classes}

    # ── 正常训练模式（从头开始，两阶段迁移学习） ───────────────────────
    # Phase 1 用较高固定 LR（不衰减），让分类头在 ImageNet 特征上快速收敛
    freeze_epochs = max(1, epochs // 3)
    _freeze_backbone(model, model_type)
    head_params = [p for p in model.parameters() if p.requires_grad]
    phase1_lr = max(lr * 10, 1e-3)
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
    parser.add_argument("--resume",     action="store_true",
                        help="从已有最优检查点继续 Phase 2 微调，跳过 Phase 1")
    parser.add_argument("--grad-accum", type=int,   default=1,
                        help="梯度累积步数（模拟更大 batch_size）")
    args = parser.parse_args()
    result = run_training(args.model, args.epochs, args.batch_size, args.lr,
                          resume=args.resume, grad_accum=args.grad_accum)
    logger.info("Training complete: %s", result)
