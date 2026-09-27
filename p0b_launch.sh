#!/bin/bash
cd /root/autodl-tmp
bash rtl-rlvr/configs/grpo/run_p0b.sh > rtl-rlvr/logs/p0b_train.log 2>&1
echo P0B_EXIT=$? >> rtl-rlvr/logs/p0b_train.log
