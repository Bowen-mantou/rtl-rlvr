#!/bin/bash
# E3 GRPO 启动（关键：从数据盘 cwd 启动，checkpoint 位置由 cwd 决定——PITFALLS 红线）
cd /root/autodl-tmp
bash rtl-rlvr/configs/grpo/run_grpo.sh > rtl-rlvr/logs/e3_train.log 2>&1
echo "E3_EXIT=$?" >> rtl-rlvr/logs/e3_train.log
