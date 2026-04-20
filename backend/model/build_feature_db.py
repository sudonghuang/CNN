"""
独立特征库构建脚本 — 在新进程中运行，避免训练后 OOM

用法：
  python model/build_feature_db.py --model resnet50
  python model/build_feature_db.py --model vgg16
"""
import os, sys, json, argparse, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
from collections import defaultdict
from torch.utils.data import DataLoader
from torchvision import datasets

from model.train import (build_model, get_transforms, _forward_embedding,
                         CHECKPOINT_DIR, TRAIN_DIR, DATASET_ROOT, FEATURE_DB_PATH)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build(model_type: str):
    device = torch.device("cpu")
    meta_path = os.path.join(CHECKPOINT_DIR, f"{model_type}_meta.json")
    ckpt_path = os.path.join(CHECKPOINT_DIR, f"{model_type}_best.pth")

    if not os.path.exists(ckpt_path):
        logger.error("权重文件不存在: %s", ckpt_path)
        sys.exit(1)

    with open(meta_path) as f:
        meta = json.load(f)
    num_classes = meta["num_classes"]

    logger.info("加载模型 %s，num_classes=%d", model_type, num_classes)
    model = build_model(model_type, num_classes, pretrained=False).to(device)
    model.load_state_dict(torch.load(ckpt_path, map_location=device, weights_only=True))
    model.eval()

    # 使用 train 目录（ImageFolder），文件夹名 = 人名/学号
    src_dir = TRAIN_DIR if os.path.isdir(TRAIN_DIR) else DATASET_ROOT
    dataset = datasets.ImageFolder(src_dir, transform=get_transforms(False))
    loader  = DataLoader(dataset, batch_size=8, shuffle=False, num_workers=0)
    logger.info("数据集: %d 张，%d 类", len(dataset), len(dataset.classes))

    class_to_feats: dict = defaultdict(list)
    with torch.no_grad():
        for imgs, labels in loader:
            feats = _forward_embedding(model, model_type, imgs.to(device))
            feats = torch.nn.functional.normalize(feats, p=2, dim=1)
            for f, l in zip(feats.cpu().numpy(), labels.numpy()):
                class_to_feats[int(l)].append(f)

    idx_to_class = {v: k for k, v in dataset.class_to_idx.items()}

    # 尝试从数据库取 db_id（在 Flask 上下文外则置 -1）
    student_id_to_db_id: dict = {}
    try:
        from app.models.student import Student
        from app.extensions import db
        rows = db.session.query(Student.student_id, Student.id).all()
        student_id_to_db_id = {r.student_id: r.id for r in rows}
        logger.info("从数据库匹配到 %d 条学生记录", len(student_id_to_db_id))
    except Exception as e:
        logger.warning("数据库查询跳过（Flask上下文不可用）: %s", e)

    student_ids, db_ids, feature_matrix = [], [], []
    for class_idx, feats in class_to_feats.items():
        avg = np.mean(feats, axis=0)
        avg = avg / (np.linalg.norm(avg) + 1e-8)
        sid = idx_to_class[class_idx]
        did = student_id_to_db_id.get(sid, -1)
        student_ids.append(sid)
        db_ids.append(did)
        feature_matrix.append(avg)

    np.save(FEATURE_DB_PATH, {
        "student_ids": student_ids,
        "db_ids": db_ids,
        "feature_matrix": np.array(feature_matrix),
    })
    logger.info("特征库已保存: %d 人 → %s", len(student_ids), FEATURE_DB_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="resnet50", choices=["vgg16", "resnet50"])
    args = parser.parse_args()
    build(args.model)
