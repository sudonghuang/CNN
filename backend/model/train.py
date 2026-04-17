"""
迁移学习训练脚本
用法：python model/train.py --model resnet50 --epochs 30
"""
import os
import sys
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

DATASET_ROOT = os.path.join(os.path.dirname(__file__), "..", "dataset", "faces")
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
    if model_type == "vgg16":
        weights = models.VGG16_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.vgg16(weights=weights)
        model.classifier = nn.Sequential(
            nn.Linear(25088, 4096), nn.ReLU(True), nn.Dropout(0.5),
            nn.Linear(4096, 512),  nn.ReLU(True), nn.Dropout(0.5),
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


def run_training(model_type: str = "resnet50", epochs: int = 30,
                 batch_size: int = 32, lr: float = 1e-4) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training %s on %s", model_type, device)

    # 数据集
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
    train_loader = DataLoader(train_ds, batch_size=batch_size,
                              shuffle=True, num_workers=2)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size,
                              shuffle=False, num_workers=2)
    num_classes = len(full_ds.classes)
    logger.info("Classes: %d  Train: %d  Val: %d", num_classes, len(train_ds), len(val_ds))

    model = build_model(model_type, num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.1)

    best_acc, best_epoch = 0.0, 0
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    for epoch in range(1, epochs + 1):
        # 训练
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
            preds = out.argmax(1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
        train_acc = correct / total
        # 验证
        model.eval()
        vcorrect, vtotal = 0, 0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                preds = model(imgs).argmax(1)
                vcorrect += (preds == labels).sum().item()
                vtotal += labels.size(0)
        val_acc = vcorrect / vtotal
        scheduler.step()
        logger.info("Epoch %d/%d  loss=%.4f  train_acc=%.4f  val_acc=%.4f",
                    epoch, epochs, running_loss / len(train_loader), train_acc, val_acc)
        if val_acc > best_acc:
            best_acc = val_acc
            best_epoch = epoch
            ckpt = os.path.join(CHECKPOINT_DIR, f"{model_type}_best.pth")
            torch.save(model.state_dict(), ckpt)
            logger.info("Saved best checkpoint: %s (val_acc=%.4f)", ckpt, best_acc)

    # 提取特征库
    _extract_feature_db(model, model_type, full_ds, device, num_classes)
    return {"best_acc": best_acc, "best_epoch": best_epoch}


def _extract_feature_db(model, model_type, dataset, device, num_classes):
    """用训练好的模型为所有学生提取特征，保存至 features.npy"""
    import numpy as np
    from collections import defaultdict

    # 去掉分类头，保留特征层
    if model_type == "vgg16":
        feat_model = nn.Sequential(*list(model.children())[:-1],
                                    nn.Flatten(), nn.Linear(25088, 512))
        # 从 classifier 复制权重
        feat_model[-1].weight = model.classifier[-1].weight if hasattr(
            model.classifier[-1], 'weight') else feat_model[-1].weight
    else:
        feat_model = nn.Sequential(*list(model.children())[:-1], nn.Flatten())

    feat_model = feat_model.to(device)
    feat_model.eval()
    transform = get_transforms(False)

    class_to_feats = defaultdict(list)
    loader = DataLoader(dataset, batch_size=32, shuffle=False)
    all_idx = 0
    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            try:
                feats = feat_model(imgs).cpu().numpy()
            except Exception:
                continue
            for f, l in zip(feats, labels.numpy()):
                class_to_feats[int(l)].append(f)

    student_ids, db_ids, feature_matrix = [], [], []
    idx_to_class = {v: k for k, v in dataset.class_to_idx.items()}
    for class_idx, feats in class_to_feats.items():
        avg = np.mean(feats, axis=0)
        avg = avg / (np.linalg.norm(avg) + 1e-8)
        student_id = idx_to_class[class_idx]
        student_ids.append(student_id)
        db_ids.append(class_idx)  # 占位，实际需对应数据库 ID
        feature_matrix.append(avg)

    if feature_matrix:
        np.save(FEATURE_DB_PATH, {
            "student_ids": student_ids,
            "db_ids": db_ids,
            "feature_matrix": np.array(feature_matrix),
        })
        logger.info("Feature DB saved: %d students → %s", len(student_ids), FEATURE_DB_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="resnet50", choices=["vgg16", "resnet50"])
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()
    result = run_training(args.model, args.epochs, args.batch_size, args.lr)
    logger.info("Training complete: %s", result)
