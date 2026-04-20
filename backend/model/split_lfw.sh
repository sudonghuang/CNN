#!/bin/bash
# LFW 筛选与划分
# 默认：取图片最多的 Top-50 人（对应真实课堂规模，训练快、精度高）
#
# 用法：
#   bash model/split_lfw.sh              # Top-50，推荐
#   bash model/split_lfw.sh --top 50     # 同上
#   bash model/split_lfw.sh --top 158    # ≥10张的所有人（慢，6小时）
#   bash model/split_lfw.sh --min 6      # 按最少图片数筛选

LFW_DIR="$(cd "$(dirname "$0")" && pwd)/lfw_raw/lfw"
OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/dataset/faces"
TOP_N=50      # 取图片最多的前 N 人（0=不限制，由 MIN_IMAGES 控制）
MIN_IMAGES=10 # 当 TOP_N=0 时生效

# 解析参数
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --top)  TOP_N="$2";   shift ;;
    --min)  MIN_IMAGES="$2"; TOP_N=0; shift ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
  shift
done

echo "============================================"
echo "  LFW 数据集划分"
echo "============================================"
echo "  LFW 源目录: $LFW_DIR"
echo "  输出目录:   $OUT_DIR"
if [ "$TOP_N" -gt 0 ]; then
  echo "  模式: Top-$TOP_N 人（按图片数降序）"
else
  echo "  模式: 每人 >= $MIN_IMAGES 张"
fi
echo ""

if [ ! -d "$LFW_DIR" ]; then
  echo "[error] LFW 目录不存在: $LFW_DIR"
  echo "请先运行: bash model/split_lfw.sh  (LFW 应已解压到 model/lfw_raw/lfw/)"
  exit 1
fi

# ── 第一步：统计每个人的图片数，排序后筛选 ───────────────────────────

TMPFILE=$(mktemp)
for person_dir in "$LFW_DIR"/*/; do
  count=$(ls "$person_dir"*.jpg 2>/dev/null | wc -l)
  if [ "$count" -ge "$MIN_IMAGES" ]; then
    echo "$count $person_dir"
  fi
done | sort -rn > "$TMPFILE"

total_available=$(wc -l < "$TMPFILE")
echo "[filter] ≥$MIN_IMAGES 张的人数: $total_available"

# 如果指定了 TOP_N，只取前 N 行
if [ "$TOP_N" -gt 0 ]; then
  head -n "$TOP_N" "$TMPFILE" > "${TMPFILE}.top"
  mv "${TMPFILE}.top" "$TMPFILE"
  echo "[filter] 取 Top-$TOP_N"
fi

selected=$(wc -l < "$TMPFILE")
echo "[filter] 最终选定人数: $selected"
echo ""

# ── 第二步：清空旧数据，创建目录 ─────────────────────────────────────

rm -rf "$OUT_DIR/train" "$OUT_DIR/val" "$OUT_DIR/test"
mkdir -p "$OUT_DIR/train" "$OUT_DIR/val" "$OUT_DIR/test"

# ── 第三步：按 70/20/10 复制图片 ─────────────────────────────────────

echo "[split] 开始划分并复制图片..."
processed=0

while read -r count person_dir; do
  person_name=$(basename "$person_dir")
  imgs=("$person_dir"*.jpg)
  n=${#imgs[@]}

  n_train=$(echo "$n * 70 / 100" | bc)
  [ "$n_train" -lt 1 ] && n_train=1
  n_val=$(echo "$n * 20 / 100" | bc)
  [ "$n_val" -lt 1 ] && n_val=1
  n_test=$((n - n_train - n_val))
  [ "$n_test" -lt 1 ] && n_test=1
  if [ $((n_train + n_val + n_test)) -gt "$n" ]; then
    n_val=$((n_val - 1))
  fi

  mkdir -p "$OUT_DIR/train/$person_name"
  mkdir -p "$OUT_DIR/val/$person_name"
  mkdir -p "$OUT_DIR/test/$person_name"

  idx=0
  for img in "${imgs[@]}"; do
    fname=$(basename "$img")
    if [ "$idx" -lt "$n_train" ]; then
      cp "$img" "$OUT_DIR/train/$person_name/$fname"
    elif [ "$idx" -lt $((n_train + n_val)) ]; then
      cp "$img" "$OUT_DIR/val/$person_name/$fname"
    elif [ "$idx" -lt $((n_train + n_val + n_test)) ]; then
      cp "$img" "$OUT_DIR/test/$person_name/$fname"
    fi
    idx=$((idx + 1))
  done

  processed=$((processed + 1))
  printf "  进度: %d/%d\r" "$processed" "$selected"
done < "$TMPFILE"

rm -f "$TMPFILE"
echo ""

# ── 第四步：统计结果 ─────────────────────────────────────────────────

train_count=$(find "$OUT_DIR/train" -name "*.jpg" 2>/dev/null | wc -l)
val_count=$(find "$OUT_DIR/val"   -name "*.jpg" 2>/dev/null | wc -l)
test_count=$(find "$OUT_DIR/test" -name "*.jpg" 2>/dev/null | wc -l)
total_split=$((train_count + val_count + test_count))

echo "============================================"
echo "  数据集准备完成"
echo "============================================"
echo "  类别数（人物）: $selected"
printf "  train: %5d 张  (%.0f%%)\n" "$train_count" "$(echo "scale=0; $train_count * 100 / $total_split" | bc)"
printf "  val:   %5d 张  (%.0f%%)\n" "$val_count"   "$(echo "scale=0; $val_count * 100 / $total_split" | bc)"
printf "  test:  %5d 张  (%.0f%%)\n" "$test_count"  "$(echo "scale=0; $test_count * 100 / $total_split" | bc)"
echo "  总计:  $total_split 张"
echo ""
echo "  目录结构: dataset/faces/{train,val,test}/<person>/*.jpg"
echo "============================================"
echo ""
echo "下一步训练（预计 90-120 分钟）："
echo "  source .venv/bin/activate"
echo "  PYTHONPATH=\"\$HOME/.local/lib/python3.10/site-packages\" \\"
echo "    python model/train.py --model resnet50 --epochs 30 --batch-size 64"
