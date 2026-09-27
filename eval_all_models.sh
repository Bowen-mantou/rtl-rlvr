#!/bin/bash
# 三模型终局评估（扩展评估集 50 题：自建 14 + VerilogEval 36），顺序执行
cd /root/autodl-tmp/rtl-rlvr
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    data/verilogeval_cleaned.jsonl \
    --model /root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct \
    --split eval --out-dir results/e1_final > logs/e1_final.log 2>&1
echo "E1_FINAL_EXIT=$?" >> logs/e1_final.log
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    data/verilogeval_cleaned.jsonl \
    --model /root/autodl-tmp/models/e2-sft-merged \
    --split eval --out-dir results/e2_final > logs/e2_final.log 2>&1
echo "E2_FINAL_EXIT=$?" >> logs/e2_final.log
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    data/verilogeval_cleaned.jsonl \
    --model /root/autodl-tmp/models/e3-final-3b-v2 \
    --split eval --out-dir results/e3_final > logs/e3_final.log 2>&1
echo "E3_FINAL_EXIT=$?" >> logs/e3_final.log
echo "ALL_EVALS_DONE" >> logs/e3_final.log
