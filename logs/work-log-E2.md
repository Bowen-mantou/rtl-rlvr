# Work-Log：E2（SFT）

- 日期：2026-09-20
- 实例 / 卡型：AutoDL A800 80GB（无卡模式装环境后切换）
- 一句话目标：LLaMA-Factory LoRA SFT 学 Verilog 语法与格式

## 配置

| 项 | 值 |
|---|---|
| 模型 | Qwen2.5-Coder-3B-Instruct + LoRA(rank 32 / alpha 64) |
| 框架 | LLaMA-Factory 0.9.6.dev0（venv /root/llamafactory-env，复用系统 torch 2.11） |
| 训练数据 | 102 条（自建 40 + VerilogEval V2 train 62），alpaca 格式，qwen 模板 |
| 超参 | 3 epochs / batch 4×gradacc4 / lr 5e-5 cosine / warmup 0.1 / bf16 |
| 评估集 | 与 E1 完全同脚本同命令（46 题，贪心 n=1） |

## 命令

```bash
/root/llamafactory-env/bin/llamafactory-cli train configs/sft/llamafactory_sft.yaml
/root/llamafactory-env/bin/llamafactory-cli export ...（合并 LoRA → e2-sft-merged）
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    data/verilogeval_cleaned.jsonl --model /root/autodl-tmp/models/e2-sft-merged \
    --split eval --out-dir results/e2
```

## 跑分

| 指标 | E1 | E2 | Δ |
|---|---|---|---|
| pass@1 | 0.3696 | **0.6087** | **+0.239** |
| 综合通过率 | 0.9130 | 0.9783 | +0.065 |
| 仿真通过率 | 0.3696 | 0.6087 | +0.239 |
| 格式达标率 | 1.0 | 1.0 | 0 |
| combinational | 0.2812 | 0.5938（综合率 1.0） | +0.313 |
| sequential | 0.6667 | 0.7500 | +0.083 |
| fsm | 0.0000 | 0.0000 | 0 |

训练指标：train_loss 0.343 → 0.271（3 epochs，21 步，43 秒）；loss 曲线见
checkpoints/sft/e2-lora/training_loss.png；逐 step 记录 trainer_log.jsonl。

## 拟合状态分析（面试材料）

- 无过拟合证据：评估集是训练集外问题（+23.9pp 泛化提升）；loss 未趋 0
- 有轻度欠拟合：loss 后 0.8 epoch 平台期（0.223→0.221）；训练仅 21 步
- FSM 0% = 技能级欠拟合：训练数据含 8 道状态机题但评估 2 题全不会——
  8 例不足以泛化状态机设计模式，这正是 E3 GRPO 的靶子
- 口径说明：yaml 未配 val_size（评估集独立管理），拟合判定靠行为评估
  （双闸 pass@1）而非 loss 曲线——RTL 域有可验证奖励，比 loss 更接近能力

## 坑

1. LLaMA-Factory 安装四连坑（gh-proxy 慢 / PyPI 无包 / 清华源 403 / av 轮子
   375KB 卡死）→ 最终：codeload tarball + venv --system-site-packages +
   双镜像 + aria2（记录于 configs/sft/命令清单.md）
2. 训练 OMP_NUM_THREADS 环境变量非法告警（无害，launch 时显式设为 8）

## 花费与耗时

- 训练 43 秒 + 合并 ~2 分钟 + 评估 ~12 分钟 | E2 卡时总计 ≈ ¥2
- 环境安装踩坑时间约 1.5 小时（无卡模式 ¥0.1/h ≈ ¥0.2）

## 下一步

- E2 结论：SFT 大幅涨功能（非仅格式）——数据小但同分布强化效果好；
  FSM 不动 → E3 GRPO 执行奖励接力
