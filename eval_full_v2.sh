#!/bin/bash
# 全量 VerilogEval V2 官方口径评估（98 题全量，pass@1, n=1, 贪心）
# 诚实口径说明：98 题中 62 题曾进入 GRPO 训练池（train split），评估报告会
# 按 split 分层输出 seen/unseen 两个数字——unseen 36 题才是干净的泛化口径。
cd /root/autodl-tmp/rtl-rlvr

for m in e1_base e2_sft e3_grpo; do
  case $m in
    e1_base) MODEL=/root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct; OUT=results/full_v2_e1 ;;
    e2_sft)  MODEL=/root/autodl-tmp/models/e2-sft-merged; OUT=results/full_v2_e2 ;;
    e3_grpo) MODEL=/root/autodl-tmp/models/e3-final-3b; OUT=results/full_v2_e3 ;;
  esac
  python scripts/eval_rtl.py pipe --problems data/verilogeval_cleaned.jsonl \
      --model $MODEL --split all --out-dir $OUT > logs/full_v2_$m.log 2>&1
  echo "${m}_EXIT=$?" >> logs/full_v2_$m.log
done
echo "FULL_V2_ALL_DONE" >> logs/full_v2_e3_grpo.log
