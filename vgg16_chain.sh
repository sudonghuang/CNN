#!/bin/bash
# VGG16 自动续训链：等待第一轮 → 评估 → 第二轮 → 评估 → 对比报告
cd /home/ubuntu/grad_design

echo "=== [1/4] 等待第一轮训练完成 (PID=1146665) $(date) ==="
while kill -0 1146665 2>/dev/null; do sleep 60; done
echo "=== 第一轮完成 $(date) ==="

echo "=== [2/4] 评估第一轮 ==="
python3 backend/model/evaluate.py --model vgg16 2>&1
cp backend/model/checkpoints/vgg16_eval.json /home/ubuntu/grad_design/vgg16_eval_r1.json

echo "=== [3/4] 第二轮续训 lr=2e-5, 15轮 $(date) ==="
python3 backend/model/train.py \
  --model vgg16 \
  --epochs 15 \
  --batch-size 4 \
  --lr 2e-5 \
  --resume \
  --grad-accum 4 \
  2>&1 | tee /home/ubuntu/grad_design/vgg16_round2.log
echo "=== 第二轮完成 $(date) ==="

echo "=== [4/4] 评估第二轮 ==="
python3 backend/model/evaluate.py --model vgg16 2>&1
cp backend/model/checkpoints/vgg16_eval.json /home/ubuntu/grad_design/vgg16_eval_r2.json

echo ""
echo "========== 最终对比 =========="
echo "--- 第一轮后 (lr=5e-5, 25轮) ---"
cat /home/ubuntu/grad_design/vgg16_eval_r1.json
echo ""
echo "--- 第二轮后 (lr=2e-5, 15轮) ---"
cat /home/ubuntu/grad_design/vgg16_eval_r2.json
echo "ALL_DONE $(date)"
