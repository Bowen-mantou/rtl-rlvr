# RTL-RLVR：可验证奖励的 RTL 代码后训练（VeriRL mini 复现）

用「Yosys 综合 + Verilator 仿真」双闸作为可验证奖励，在 Qwen2.5-Coder-3B 上
复现 RLVR 管线。RTL 的奖励比软件代码更干净——仿真没有运行时不确定性，
RLVR 的完美落地场景。总花费约 ¥50。

## 结果（双口径，诚实报告）

| 口径 | 零样本 | 最终模型 | Δ |
|---|---|---|---|
| VerilogEval V2 全集 98 题 | 20.4% | **50.0%** | +29.6 |
| 其中难题 62 题 | 9.7% | **41.0%** | +31.3（3.2×） |
| 未见题 50 题（从未进训练） | 34.0% | 60.0%* | +26.0 |

*未见题 60.0% 由最简管线（SFT+GRPO）达到——**小数据下分布内提升与泛化脱钩**
是本项目最重要的发现，详见 [docs/结论.md](docs/结论.md)。

## 五条核心结论

1. **SFT 教语法、GRPO 教功能**：状态机 SFT 一题教不会（0/6），GRPO 教出 2/6
2. **过程分档奖励不如二值奖励**：拆分奖励（综合 0.3+仿真 0.7）全口径落败
3. **n=8 + 过滤全对/全错组 = 难题特化配方**：难题 +5.2pp
4. **66 步是小数据 GRPO 的最优停止点**（132 步过拟合）
5. **未见题口径揭示分布内提升与泛化脱钩**：泛化冠军是最简管线

## 快速开始

```bash
sudo apt install -y yosys verilator build-essential
python scripts/build_spec_set.py --verify   # 数据诚信自检（必须全绿）
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    --model <任何 HF 模型路径> --split eval --out-dir results/e1
```

完整复现流程见 [docs/TUTORIAL.md](docs/TUTORIAL.md)；
操作手册 [RUNBOOK.md](RUNBOOK.md)；
踩坑手册 [docs/PITFALLS.md](docs/PITFALLS.md)。

## 目录

```
scripts/                 数据管线 + 双闸引擎 + 评估（rtl_common.py 为评估与
                         奖励共用的同一份判分实现——口径纪律）
configs/sft/             LLaMA-Factory SFT/DPO 配置
configs/grpo/            veRL GRPO 配置 + reward_fn.py
configs/verifier/        RTL verifier（可选）
data/spec_set_50.jsonl   自建 54 题 spec 集（参考实现全部通过双闸自检）
docs/                    结论 / 实验全景 / 教程 / 调研 / 踩坑手册 / 简历素材
logs/work-log-*.md       每实验完整记录（含作废记录）
```

## 方法

```
SFT 冷启动 → 双闸奖励 GRPO（配方对照）→ DeepSeek 蒸馏/模型自举扩数据
  → 偏好对 DPO → 双闸奖励 GRPO 收尾
```

## 引用与相关论文

VeriRL / RTLCoder / VeriCoder / VeriPrefer / VeriReason / VeriContaminated
调研见 [docs/调研-RTL论文.md](docs/调研-RTL论文.md)。

## License

MIT
