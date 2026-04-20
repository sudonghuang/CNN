"""
LFW 数据集下载、筛选与划分脚本

决策说明：
  - 筛选每人 ≥ 10 张的人物，共约 158 人，总图片约 5,700 张
  - 理由：每人 10 张保证训练集有 7 张 + 数据增强，类别少但每类样本充足
          CPU 环境下训练速度快，单 epoch < 1 分钟，30 epoch 约 25 分钟
          158 个类别的闭集识别，Top-1 ≥ 90% 完全可达，远超任务书 85% 目标
  - 划分：train 70% / val 20% / test 10%（按人物固定 seed 随机分配）
  - 测试集全程封存，仅用于最终指标报告

用法：
  python model/prepare_lfw.py
  python model/prepare_lfw.py --min-images 6   # 换成 ≥6 张，约 430 人
"""

import os
import sys
import shutil
import tarfile
import random
import argparse
import urllib.request
from pathlib import Path
from collections import defaultdict

# 官方 lfw.tgz 服务器不稳定，使用 sklearn 维护的 figshare 镜像（funneled 版，文件夹结构相同）
LFW_URL = "https://ndownloader.figshare.com/files/5976018"
LFW_FILENAME = "lfw_funneled.tgz"
LFW_INNER_DIR = "lfw"  # figshare 镜像解压后顶层目录名
SCRIPT_DIR = Path(__file__).parent
DOWNLOAD_DIR = SCRIPT_DIR / "lfw_raw"
DATASET_ROOT = SCRIPT_DIR.parent / "dataset" / "faces"

SPLIT_RATIOS = {"train": 0.70, "val": 0.20, "test": 0.10}
RANDOM_SEED = 42


def download_lfw(download_dir: Path):
    import subprocess
    download_dir.mkdir(parents=True, exist_ok=True)
    tgz_path = download_dir / LFW_FILENAME
    lfw_dir = download_dir / LFW_INNER_DIR

    if lfw_dir.exists():
        print(f"[skip] LFW 已解压到 {lfw_dir}")
        return lfw_dir

    if not tgz_path.exists():
        print(f"[download] 正在下载 LFW funneled ({LFW_URL}) ...")
        print("  文件约 173MB，请稍候...\n")
        ret = subprocess.run(
            ["wget", "-L", "--progress=bar:force", "-O", str(tgz_path), LFW_URL],
            check=False,
        )
        if ret.returncode != 0 or not tgz_path.exists() or tgz_path.stat().st_size < 1e6:
            if tgz_path.exists():
                tgz_path.unlink()
            print("[error] 下载失败，请检查网络连接后重试")
            sys.exit(1)
        print(f"\n[done] 下载完成: {tgz_path} ({tgz_path.stat().st_size / 1e6:.1f} MB)")
    else:
        print(f"[skip] 已有压缩包: {tgz_path} ({tgz_path.stat().st_size / 1e6:.1f} MB)")

    print(f"[extract] 正在解压...")
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(download_dir)
    print(f"[done] 解压完成: {lfw_dir}")
    return lfw_dir


def collect_images(lfw_dir: Path, min_images: int) -> dict:
    """按人名收集图片路径，只保留图片数 >= min_images 的人"""
    people = defaultdict(list)
    for person_dir in sorted(lfw_dir.iterdir()):
        if not person_dir.is_dir():
            continue
        imgs = sorted(person_dir.glob("*.jpg"))
        if len(imgs) >= min_images:
            people[person_dir.name] = [str(p) for p in imgs]

    print(f"[filter] min_images={min_images} → 符合条件人数: {len(people)}")
    total = sum(len(v) for v in people.values())
    print(f"         总图片数: {total}")
    avg = total / len(people) if people else 0
    print(f"         平均每人: {avg:.1f} 张")
    return dict(people)


def split_and_copy(people: dict, dataset_root: Path, seed: int = RANDOM_SEED):
    """将图片按 train/val/test 划分并复制"""
    rng = random.Random(seed)

    # 清空旧数据
    if dataset_root.exists():
        print(f"[clean] 清空旧数据集目录: {dataset_root}")
        shutil.rmtree(dataset_root)

    for split in SPLIT_RATIOS:
        (dataset_root / split).mkdir(parents=True, exist_ok=True)

    stats = {"train": 0, "val": 0, "test": 0}

    for person_name, img_paths in people.items():
        imgs = img_paths[:]
        rng.shuffle(imgs)
        n = len(imgs)

        n_train = max(1, round(n * SPLIT_RATIOS["train"]))
        n_val = max(1, round(n * SPLIT_RATIOS["val"]))
        # 剩余全给 test（保证至少 1 张）
        n_test = max(1, n - n_train - n_val)
        # 调整避免溢出
        if n_train + n_val + n_test > n:
            n_val -= 1

        splits_imgs = {
            "train": imgs[:n_train],
            "val":   imgs[n_train:n_train + n_val],
            "test":  imgs[n_train + n_val:n_train + n_val + n_test],
        }

        for split, split_imgs in splits_imgs.items():
            dest_dir = dataset_root / split / person_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            for src in split_imgs:
                dst = dest_dir / Path(src).name
                shutil.copy2(src, dst)
                stats[split] += 1

    return stats


def print_summary(people: dict, stats: dict, dataset_root: Path):
    print("\n" + "=" * 55)
    print("  数据集准备完成")
    print("=" * 55)
    print(f"  类别数（人物数）: {len(people)}")
    print(f"  train: {stats['train']} 张  ({stats['train'] / sum(stats.values()) * 100:.1f}%)")
    print(f"  val:   {stats['val']} 张  ({stats['val'] / sum(stats.values()) * 100:.1f}%)")
    print(f"  test:  {stats['test']} 张  ({stats['test'] / sum(stats.values()) * 100:.1f}%)")
    print(f"  总计:  {sum(stats.values())} 张")
    print(f"\n  目录: {dataset_root}")
    print(f"  结构: {dataset_root}/train/<person>/<img>.jpg")
    print("=" * 55)
    print("\n下一步训练命令：")
    print("  python model/train.py --model resnet50 --epochs 30")
    print("  python model/train.py --model vgg16 --epochs 30")


def main():
    parser = argparse.ArgumentParser(description="LFW 数据集准备脚本")
    parser.add_argument("--min-images", type=int, default=10,
                        help="每人最少图片数，默认 10（约 158 人）")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED,
                        help="随机种子，默认 42")
    args = parser.parse_args()

    print(f"配置：min_images={args.min_images}, seed={args.seed}")
    print(f"下载目录: {DOWNLOAD_DIR}")
    print(f"输出目录: {DATASET_ROOT}\n")

    lfw_dir = download_lfw(DOWNLOAD_DIR)
    people = collect_images(lfw_dir, min_images=args.min_images)

    if not people:
        print(f"[error] 没有找到 >= {args.min_images} 张的人物，请降低 --min-images")
        sys.exit(1)

    print(f"\n[split] 开始划分并复制图片 (seed={args.seed})...")
    stats = split_and_copy(people, DATASET_ROOT, seed=args.seed)
    print_summary(people, stats, DATASET_ROOT)


if __name__ == "__main__":
    main()
