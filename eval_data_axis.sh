#!/bin/bash
# 数据轴三模型评估（152 题全量，同脚本同采样）
cd /root/autodl-tmp/rtl-rlvr
for m in e6 e5 mix; do
  case $m in
    e6)  MODEL=/root/autodl-tmp/models/e6-sft-merged; OUT=results/data_axis_e6 ;;
    e5)  MODEL=/root/autodl-tmp/models/e5-sft-merged; OUT=results/data_axis_e5 ;;
    mix) MODEL=/root/autodl-tmp/models/mix-sft-merged; OUT=results/data_axis_mix ;;
  esac
  python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
      data/verilogeval_cleaned.jsonl --model $MODEL --split all \
      --out-dir $OUT > logs/data_axis_$m.log 2>&1
  echo "${m}_EXIT=$?" >> logs/data_axis_$m.log
done
echo "DATA_AXIS_ALL_DONE" >> logs/data_axis_mix.log
