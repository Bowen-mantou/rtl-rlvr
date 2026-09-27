# RTL-RLVR 教程：用双闸可验证奖励在 RTL 域复现 RLVR

> 一句话卖点：**RTL 的奖励比软件代码更干净**——Yosys 综合 + Verilator 仿真
> 没有运行时不确定性，是 RLVR（可验证奖励强化学习）的完美落地场景。
> 本项目在 Qwen2.5-Coder-3B 上完成 VeriRL 的 mini 复现（总花费约 ¥50）。

## 0. 30 秒理解

任务 = 代码生成（和「题目→Python」同构，目标语言换成 Verilog）：

```
输入 spec："写一个 8 位计数器，带同步复位和使能"
模型输出：module counter (...) ... endmodule
判分（双闸）：
  ① Yosys 综合 —— 语法对不对、能不能变成电路（≈ 编译通过）
  ② Verilator 仿真 —— 真实运行电路、逐拍比对输出（≈ 单元测试通过）
  两闸全过 = 对
```

## 1. 核心结论（5 条）

| # | 结论 | 证据 |
|---|---|---|
| 1 | **SFT 教语法、GRPO 教功能** | SFT 后简单题 66.7% 但状态机 0/6；GRPO 后状态机 2/6（含 1 道未见题） |
| 2 | **过程分档奖励不如二值奖励** | 拆分奖励（综合 0.3+仿真 0.7）全口径落败，FSM -19pp |
| 3 | **组采样 n=8 + 过滤全对/全错组 = 难题特化配方** | 难题 +5.2pp；代价：简单题退化（DAPO 全对组被滤的副作用） |
| 4 | **66 步是小数据 GRPO 的最优停止点** | 132 步训练奖励继续涨（0.44→0.79）但泛化崩（60→50） |
| 5 | **小数据下分布内提升与泛化脱钩** | 全管线在训练分布内 32.7→50.0，但未见题上最简 SFT+GRPO 管线最好（60.0%） |

## 2. 最终结果（双口径，诚实报告）

| 口径 | 零样本 | 最终模型 | Δ |
|---|---|---|---|
| VerilogEval V2 全集 98 题 | 20.4% | 50.0% | +29.6 |
| 其中难题 62 题 | 9.7% | 41.0% | +31.3（3.2×） |
| 未见题 50 题（从未进训练） | 34.0% | 60.0%* | +26.0 |

*未见题 60.0% 由最简管线（SFT+GRPO）达到；最终模型为 54.9%——这就是结论 5。

## 3. 方法：五阶段管线

```
SFT 冷启动（102 条参考实现）
  → 双闸奖励 GRPO（配方对照：二值 / 拆分 / n=8+组过滤）
  → DeepSeek 蒸馏 + 模型自举扩数据（双闸过滤后 391 条三源 SFT）
  → 偏好对 DPO（双闸标注轨迹构对 26 对）
  → 双闸奖励 GRPO 收尾
```

奖励设计（GRPO 用）：

```
总奖励 = 格式 + 正确性（满分 1.1）
  格式：<answer> 内解析出完整 module（+0.1）；解析失败（-0.1）
  正确性：综合失败 → 0；综合过 + 仿真全过 → 1.0；部分过 → 0（二值）
```

## 4. 如何复现（最小闭环，半天）

```bash
# 1) 环境
sudo apt install -y yosys verilator build-essential
pip install verl  # 或按 veRL 官方安装

# 2) 数据（自建 54 题，参考实现先过自己的双闸才入库）
python scripts/build_spec_set.py          # 生成 data/spec_set_50.jsonl
python scripts/build_spec_set.py --verify # 数据诚信自检，必须全绿

# 3) 任意 HF 模型零样本评估（eval_rtl.py 与训练奖励共用同一份双闸实现）
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    --model <模型路径> --split eval --out-dir results/e1

# 4) 训练数据准备（veRL parquet + LLaMA-Factory alpaca）
python scripts/make_grpo_parquet.py --problems data/spec_set_50.jsonl \
    --split train --val-n 8 --out-dir data/grpo
python scripts/to_llamafactory.py --problems data/spec_set_50.jsonl \
    --split train --out data/sft/sft_alpaca.json

# 5) SFT → GRPO（配置见 configs/sft 与 configs/grpo/run_grpo.sh）
# 6) 蒸馏/自举扩数据（scripts/e5_sample_teacher.py + annotate_samples.py）
# 7) DPO（scripts/build_dpo_pairs.py + LLaMA-Factory dpo 配置）
```

## 5. 目录导览

- `scripts/rtl_common.py` — 双闸判定引擎（评估与奖励同一份实现，口径纪律）
- `scripts/eval_rtl.py` — 评估入口（分层指标：总/综合/仿真/格式通过率）
- `scripts/build_spec_set.py` — 自建 54 题 spec 集生成 + 双闸自检
- `scripts/clean_data.py` — VerilogEval V2 下载与清洗（可综合性过滤）
- `configs/grpo/reward_fn.py` — veRL 自定义奖励（设计文档第三节的逐字实现）
- `docs/实验全景.md` — 每个实验的方案/结果/决策链
- `docs/结论.md` — 结论定稿；`docs/调研-RTL论文.md` — 四篇论文调研
- `logs/work-log-*.md` — 每实验完整记录（含作废记录与踩坑）

## 6. 已知局限（如实报告）

1. 数据规模 ~250 条，为 VeriRL（92K）的 1/300——绝对数字不可比，价值在
   方法链路与消融结论的可复现性
2. 判分口径：自建题用显式测试向量（硬判分）；VerilogEval 题用参考 oracle
   （候选与参考实现同输入逐拍比对），弱于真 testbench 判分
3. DPO 仅 26 对，未见题零增量（小样本证伪，已如实标注）
4. 评估集划分曾按编号取前 N（V2 按难度排序）——教训已写入 RUNBOOK

## 7. 引用

- VeriRL (arXiv:2508.18462) / RTLCoder / VeriCoder / VeriPrefer /
  VeriReason / VeriContaminated —— 调研见 `docs/调研-RTL论文.md`
- 本项目若对你有用，欢迎 star 与引用
