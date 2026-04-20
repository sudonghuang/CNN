"""
模型评估脚本 — 输出任务书要求的全部指标

指标：Top-1 准确率、Precision、Recall、F1、AUC-ROC、FAR、FRR、推理时间
评估集：dataset/faces/test/（由 prepare_lfw.py 划分，全程封存）

用法：
  python model/evaluate.py --model resnet50
  python model/evaluate.py --model vgg16
  python model/evaluate.py --compare   # 同时评估两个模型并对比
"""

import os
import sys
import time
import json
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
from torch.utils.data import DataLoader
from torchvision import datasets

from model.train import build_model, get_transforms, _forward_embedding, CHECKPOINT_DIR

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

DATASET_ROOT = os.path.join(os.path.dirname(__file__), "..", "dataset", "faces")
TEST_DIR     = os.path.join(DATASET_ROOT, "test")


def load_model(model_type: str, device: torch.device):
    ckpt_path = os.path.join(CHECKPOINT_DIR, f"{model_type}_best.pth")
    meta_path = os.path.join(CHECKPOINT_DIR, f"{model_type}_meta.json")

    if not os.path.exists(ckpt_path):
        raise FileNotFoundError(f"找不到模型权重: {ckpt_path}\n请先运行: python model/train.py --model {model_type}")

    with open(meta_path) as f:
        meta = json.load(f)
    num_classes = meta["num_classes"]

    model = build_model(model_type, num_classes, pretrained=False).to(device)
    model.load_state_dict(torch.load(ckpt_path, map_location=device, weights_only=True))
    model.eval()
    logger.info("Loaded %s: num_classes=%d, best_val_acc=%.4f (epoch %d)",
                model_type, num_classes, meta.get("best_acc", 0), meta.get("best_epoch", 0))
    return model, num_classes


def evaluate(model_type: str) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not os.path.isdir(TEST_DIR):
        raise RuntimeError(f"测试集目录不存在: {TEST_DIR}\n请先运行: python model/prepare_lfw.py")

    test_ds = datasets.ImageFolder(TEST_DIR, transform=get_transforms(False))
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=2)
    logger.info("Test set: %d samples, %d classes", len(test_ds), len(test_ds.classes))

    model, num_classes = load_model(model_type, device)

    all_preds, all_labels, all_probs = [], [], []
    total_time_ms, total_samples = 0.0, 0

    with torch.no_grad():
        for imgs, labels in test_loader:
            imgs = imgs.to(device)
            t0 = time.perf_counter()
            logits = model(imgs)
            elapsed = (time.perf_counter() - t0) * 1000  # ms
            total_time_ms += elapsed
            total_samples += imgs.size(0)

            probs = torch.softmax(logits, dim=1).cpu().numpy()
            preds = logits.argmax(1).cpu().numpy()
            all_preds.extend(preds.tolist())
            all_labels.extend(labels.numpy().tolist())
            all_probs.append(probs)

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs  = np.vstack(all_probs)

    # ── Top-1 准确率 ──────────────────────────────────────────────
    top1 = float((all_preds == all_labels).mean())

    # ── Per-class Precision / Recall / F1 / FAR / FRR ───────────
    classes = sorted(set(all_labels.tolist()))
    class_counts = np.array([int((all_labels == c).sum()) for c in classes])
    total_n = class_counts.sum()

    prec_list, rec_list, f1_list, far_list, frr_list = [], [], [], [], []
    for c in classes:
        tp = int(((all_preds == c) & (all_labels == c)).sum())
        fp = int(((all_preds == c) & (all_labels != c)).sum())
        fn = int(((all_preds != c) & (all_labels == c)).sum())
        tn = int(((all_preds != c) & (all_labels != c)).sum())
        p   = tp / (tp + fp) if (tp + fp) else 0.0
        r   = tp / (tp + fn) if (tp + fn) else 0.0
        f1  = 2 * p * r / (p + r) if (p + r) else 0.0
        far = fp / (fp + tn) if (fp + tn) else 0.0
        frr = fn / (fn + tp) if (fn + tp) else 0.0
        prec_list.append(p)
        rec_list.append(r)
        f1_list.append(f1)
        far_list.append(far)
        frr_list.append(frr)

    weights = class_counts / total_n

    # 加权平均（weighted）：按每类样本量加权，更公平地反映整体性能
    # 宏平均（macro）：每类等权，受少样本类影响大，仅作参考
    w_precision = float(np.dot(weights, prec_list))
    w_recall    = float(np.dot(weights, rec_list))
    w_f1        = float(np.dot(weights, f1_list))
    w_far       = float(np.dot(weights, far_list))
    w_frr       = float(np.dot(weights, frr_list))

    macro_precision = float(np.mean(prec_list))
    macro_recall    = float(np.mean(rec_list))
    macro_f1        = float(np.mean(f1_list))
    macro_far       = float(np.mean(far_list))
    macro_frr       = float(np.mean(frr_list))

    # ── AUC-ROC（macro one-vs-rest，手动梯形积分） ────────────────
    auc_list = []
    for c in classes:
        y_true_bin = (all_labels == c).astype(int)
        scores = all_probs[:, c]
        # 手动计算 ROC-AUC（按阈值排序）
        sorted_idx = np.argsort(-scores)
        y_sorted = y_true_bin[sorted_idx]
        npos = y_sorted.sum()
        nneg = len(y_sorted) - npos
        if npos == 0 or nneg == 0:
            continue
        tps = np.cumsum(y_sorted)
        fps = np.cumsum(1 - y_sorted)
        tpr = tps / npos
        fpr = fps / nneg
        tpr = np.concatenate([[0], tpr])
        fpr = np.concatenate([[0], fpr])
        auc = float(np.trapz(tpr, fpr))
        auc_list.append(auc)
    macro_auc = float(np.mean(auc_list)) if auc_list else 0.0

    # ── 推理时间 ─────────────────────────────────────────────────
    ms_per_sample = total_time_ms / total_samples if total_samples else 0.0

    result = {
        "model":            model_type,
        "test_samples":     int(total_samples),
        "num_classes":      len(classes),
        "top1_acc":         round(top1, 4),
        # 加权平均（主要指标）：按每类样本量加权，适合类别不均匀的测试集
        "precision":        round(w_precision, 4),
        "recall":           round(w_recall, 4),
        "f1":               round(w_f1, 4),
        "far":              round(w_far, 4),
        "frr":              round(w_frr, 4),
        # 宏平均（参考指标）：等权平均，受少样本类影响大
        "macro_precision":  round(macro_precision, 4),
        "macro_recall":     round(macro_recall, 4),
        "macro_f1":         round(macro_f1, 4),
        "macro_far":        round(macro_far, 4),
        "macro_frr":        round(macro_frr, 4),
        "auc_roc":          round(macro_auc, 4),
        "ms_per_sample":    round(ms_per_sample, 2),
        "device":           str(device),
    }
    return result


def print_result(r: dict):
    # 主要指标（加权平均）用于达标判断
    targets = {
        "top1_acc":      ("≥ 0.85", r["top1_acc"]      >= 0.85),
        "precision":     ("≥ 0.85", r["precision"]     >= 0.85),
        "recall":        ("≥ 0.85", r["recall"]        >= 0.85),
        "f1":            ("≥ 0.85", r["f1"]            >= 0.85),
        "auc_roc":       ("≥ 0.90", r["auc_roc"]       >= 0.90),
        "far":           ("≤ 0.05", r["far"]           <= 0.05),
        "frr":           ("≤ 0.10", r["frr"]           <= 0.10),
        "ms_per_sample": ("≤ 200ms", r["ms_per_sample"] <= 200.0),
    }
    labels = {
        "top1_acc":      "Top-1 准确率",
        "precision":     "Precision (weighted)",
        "recall":        "Recall (weighted)",
        "f1":            "F1 Score (weighted)",
        "auc_roc":       "AUC-ROC (macro)",
        "far":           "FAR 误识率 (weighted)",
        "frr":           "FRR 拒识率 (weighted)",
        "ms_per_sample": "推理延迟 (ms/图)",
    }
    print(f"\n{'=' * 62}")
    print(f"  模型: {r['model'].upper()}   设备: {r['device']}")
    print(f"  测试集: {r['test_samples']} 张 / {r['num_classes']} 类")
    print(f"{'=' * 62}")
    print(f"  {'指标':<24} {'值':>10}  {'目标':>8}  达标")
    print(f"  {'-' * 54}")
    for key, (target_str, passed) in targets.items():
        val = r[key]
        val_str = f"{val:.4f}" if key != "ms_per_sample" else f"{val:.1f}ms"
        tick = "✓" if passed else "✗"
        print(f"  {labels[key]:<24} {val_str:>10}  {target_str:>8}  {tick}")
    print(f"{'=' * 62}")
    # 宏平均作为参考输出
    print(f"  参考（宏平均，受少样本类影响）：")
    print(f"    Precision={r['macro_precision']:.4f}  Recall={r['macro_recall']:.4f}"
          f"  F1={r['macro_f1']:.4f}  FRR={r['macro_frr']:.4f}")
    print(f"{'=' * 62}")
    all_pass = all(v for _, v in targets.values())
    print(f"  总体: {'全部达标 ✓' if all_pass else '部分未达标，见上'}")
    print(f"{'=' * 62}\n")


def compare_models():
    results = []
    for m in ["resnet50", "vgg16"]:
        ckpt = os.path.join(CHECKPOINT_DIR, f"{m}_best.pth")
        if not os.path.exists(ckpt):
            logger.warning("跳过 %s：权重文件不存在", m)
            continue
        logger.info("\n--- 评估 %s ---", m.upper())
        r = evaluate(m)
        print_result(r)
        results.append(r)

    if len(results) == 2:
        r1, r2 = results
        print(f"\n{'=' * 60}")
        print(f"  对比摘要: {r1['model'].upper()} vs {r2['model'].upper()}")
        print(f"{'=' * 60}")
        keys = ["top1_acc", "precision", "recall", "f1", "auc_roc", "far", "frr", "ms_per_sample"]
        labels = ["Top-1","Precision","Recall","F1","AUC","FAR","FRR","ms/图"]
        print(f"  {'指标':<12} {r1['model']:>10} {r2['model']:>10}  {'推荐'}")
        print(f"  {'-' * 44}")
        for k, lbl in zip(keys, labels):
            v1, v2 = r1[k], r2[k]
            # 越大越好（除了 FAR/FRR/ms）
            bigger_better = k not in ("far", "frr", "ms_per_sample")
            winner = r1["model"] if (v1 > v2) == bigger_better else r2["model"]
            print(f"  {lbl:<12} {v1:>10.4f} {v2:>10.4f}  ← {winner}")
        print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="模型评估脚本")
    parser.add_argument("--model", default="resnet50", choices=["vgg16", "resnet50"])
    parser.add_argument("--compare", action="store_true", help="同时评估两个模型并对比")
    args = parser.parse_args()

    if args.compare:
        compare_models()
    else:
        r = evaluate(args.model)
        print_result(r)
        out_path = os.path.join(CHECKPOINT_DIR, f"{args.model}_eval.json")
        with open(out_path, "w") as f:
            json.dump(r, f, indent=2, ensure_ascii=False)
        logger.info("评估结果已保存: %s", out_path)


if __name__ == "__main__":
    main()
