#!/bin/bash
# crash_watchdog.sh — 异常中断自动关机（正常结束不关机，留给主流程做收尾）
# 判定：main_ppo 进程消失 + 无 E3_EXIT 正常结束标记 + 进度未达总步数
# 防误杀：进程消失后先等 120 秒（e3_launch.sh 写 E3_EXIT 有极短窗口），
# 复查仍无标记才关机；正常结束（E3_EXIT 存在）时本脚本自动退出不做任何事
LOG=/root/autodl-tmp/rtl-rlvr/logs/e3_train.log
WLOG=/root/autodl-tmp/rtl-rlvr/logs/e3_crash_watchdog.log
TOTAL_STEPS=$(grep -oE 'Total steps: [0-9]+' "$LOG" | tail -1 | grep -oE '[0-9]+')
[ -z "$TOTAL_STEPS" ] && TOTAL_STEPS=66
echo "[$(date +%H:%M:%S)] crash_watchdog start (total_steps=$TOTAL_STEPS)" >> "$WLOG"

while true; do
  sleep 60
  if grep -q 'E3_EXIT=' "$LOG" 2>/dev/null; then
    echo "[$(date +%H:%M:%S)] 训练正常结束（E3_EXIT 存在），watchdog 退出" >> "$WLOG"
    exit 0
  fi
  if ! pgrep -f 'main_pp[o]' > /dev/null 2>&1; then
    echo "[$(date +%H:%M:%S)] main_ppo 消失，等 120s 复查（防正常收尾窗口误判）" >> "$WLOG"
    sleep 120
    if grep -q 'E3_EXIT=' "$LOG" 2>/dev/null; then
      echo "[$(date +%H:%M:%S)] 复查确认正常结束，watchdog 退出" >> "$WLOG"
      exit 0
    fi
    if ! pgrep -f 'main_pp[o]' > /dev/null 2>&1; then
      progress=$(tail -c 2000 "$LOG" | tr '\r' '\n' | grep -oE '[0-9]+/'"$TOTAL_STEPS" | tail -1)
      echo "[$(date +%H:%M:%S)] 确认异常中断（进度: ${progress:-未知}），关机" >> "$WLOG"
      tail -80 "$LOG" >> "$WLOG"
      /usr/bin/shutdown
      exit 0
    fi
  fi
done
