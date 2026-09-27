# Work-Log：E3（GRPO 双闸奖励）

- 日期：2026-09-21
- 实例 / 卡型：AutoDL A800 80GB（veRL main + torch 2.11 cu130）
- 一句话目标：在 E2 SFT 模型上 GRPO，用双闸执行奖励学功能正确性

## 配置

| 项 | 值 |
|---|---|
| 初始化模型 | **/root/autodl-tmp/models/e2-sft-merged**（E2 LoRA 合并模型） |
| 训练方式 | GRPO（veRL main，n=4, batch 8 题/步, kl 0.001 low_var_kl, lr 1e-6） |
| 训练数据 | 94 题（自建 40 + VerilogEval 62，减 val 8），66 步（≈ 5.5 epochs） |
| 奖励 | 双闸：格式 +0.1/-0.1，正确 1.0（满分 1.1），subprocess yosys+verilator，8 并行 + 结果缓存 |
| 评估 | 与 E1/E2 完全同脚本同命令（46 题，贪心 n=1） |

## 命令

```bash
cd /root/autodl-tmp && bash rtl-rlvr/configs/grpo/run_grpo.sh > rtl-rlvr/logs/e3_train.log 2>&1
# 守护进程：ckpt_watchdog.sh（磁盘）+ crash_watchdog.sh（崩溃关机）
# 转换 + 评估：convert_verl_ckpt.py → eval_rtl.py pipe（同 E1/E2 命令）
```

## 跑分

| 指标 | E1 | E2 | **E3** |
|---|---|---|---|
| **pass@1** | 0.3696 | 0.6087 | **0.6304** |
| 综合通过率 | 0.9130 | 0.9783 | 0.9783 |
| 仿真通过率 | 0.3696 | 0.6087 | 0.6304 |
| combinational | 0.2812 | 0.5938 | 0.5938 |
| sequential | 0.6667 | 0.7500 | 0.7500 |
| **fsm** | **0.0000** | **0.0000** | **0.5000** |

训练轨迹：reward mean 开局 ~0.2-0.3 → 末段 0.44（全程最高 0.537 @ step 55）；
rollout_corr/kl ~0.0002（权重同步健康）；entropy 0.25→0.12（策略收敛）。
逐步指标：results/e3/training_metrics.jsonl；曲线：results/e3/training_curves.png。
训练耗时 39:44（66 步 × 36.1s）；显存峰值 57.5G。

## 作废记录（诚实纪律）

- **v1 作废**（reward_model 列存 JSON 字符串）：veRL 期望 dict，TypeError 崩溃，0 步有效
- **v2 作废**（36 步）：两个独立问题叠加——① prompt 列预格式化字符串（veRL 期望
  消息列表，喂进去只剩 24 token 模板骨架，全部 reward -0.1 假训练）；② MODEL_PATH
  误指原始基座而非 e2-sft-merged（复盘时发现）。磁盘上 step 12/24/36 三个 ckpt 全删
- **v2 的磁盘崩溃**（step 48）：本版 veRL 的 max_actor_ckpt_to_keep=1 轮转实测不
  生效，三个 13G ckpt 堆积写爆 62G 数据盘 → 外部 ckpt_watchdog.sh 兜底（保留最新
  一个目录）

## 坑（全部有修复，写进 RUNBOOK §6 启动前检查清单）

1. veRL 数据契约：reward_model 列要 dict（含 ground_truth 键）；prompt 列要消息
   列表（veRL 自己套 chat 模板），不能预格式化字符串——两个都写进了 make_grpo_parquet.py
2. ckpt 轮转失效 + 磁盘账：外部 watchdog 是兜底；启动前 df -h 确认 >30G
3. 初始化契约：E3 必须从 e2-sft-merged 初始化——run_grpo.sh 加存在性断言 +
   RUNBOOK 加「人核清单」（断言拦不住「指向错误的模型」）
4. OMP_NUM_THREADS 非法值告警（无害）

## 花费与耗时

- 训练 40 分钟（含 2 次失败尝试的排查）+ 转换 3 分钟 + 评估 13 分钟
- 有效卡时 ≈ 1 小时 ≈ ¥6；失败尝试 ≈ 40 分钟 ≈ ¥4；E3 合计 ≈ ¥10

## 续训与终局（2026-09-21 凌晨补记）

- **续训**：resume 66→132 步（total_epochs 6→12）。训练集 reward 0.44→0.79，
  但扩展集评估 **pass@1 掉到 50%（E3b）**——94 题训练池翻 11 轮过拟合，
  状态机 6 题全丢。**66 步是小数据 GRPO 的最优停止点**（负面结果保留）。
- **FSM 评估集扩充**：新增 4 道未见状态机题（seqdet1001/停车场计数器/
  握手协议/消抖，全部双闸自检通过），评估集 46→50 题。
- **终局数字（扩展集 50 题，三模型同脚本同采样重评）**：
  E1 34.00% / E2 56.00% / **E3 60.00%（最优模型 = 66 步 e3-final-3b）** /
  E3b(132步) 50.00%。状态机：E1 0/6、E2 0/6、E3 2/6（含 1 道未见题 fsm-011）。
- 终局报告：results/e1_final|e2_final|e3_final|e3_final_v1/；完整曲线：
  results/e3/training_curves.png + training_metrics.jsonl（132 步全指标）。

## 下一步

- 结论已填 docs/结论.md；简历一行见其第八节
- 开源收尾（可选）：TUTORIAL 骨架填数字
