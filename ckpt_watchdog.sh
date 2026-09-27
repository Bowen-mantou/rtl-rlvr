#!/bin/bash
# ckpt_watchdog.sh v2 — 训练期磁盘守护：保留最新 checkpoint，删更旧的
# v2 安全规则（2026-09-21 教训）：最新目录里最新文件的 mtime < 300s 视为
# 「正在保存」，本轮跳过清理——防止把保存前的旧 ckpt 删了导致双失
CKPT_DIR=/root/autodl-tmp/checkpoints/rtl-rlvr/e3-p0a-split-reward
LOG=/root/autodl-tmp/rtl-rlvr/logs/p0a_watchdog.log
while true; do
  sleep 120
  dirs=$(ls -d ${CKPT_DIR}/global_step_* 2>/dev/null | sort -V)
  newest=$(echo "$dirs" | tail -1)
  [ -z "$newest" ] && continue
  newest_mtime=$(find "$newest" -type f -printf '%T@\n' 2>/dev/null | sort -n | tail -1 | cut -d. -f1)
  now=$(date +%s)
  if [ -n "$newest_mtime" ] && [ $((now - newest_mtime)) -lt 300 ]; then
    # 最新目录还在写入中 → 跳过本轮（保护旧 ckpt）
    continue
  fi
  for d in $dirs; do
    if [ "$d" != "$newest" ] && [ -d "$d" ]; then
      rm -rf "$d"
      echo "[$(date +%H:%M:%S)] removed $d" >> "$LOG"
    fi
  done
done
