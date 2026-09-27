# Work-Log：E1（零样本基线）

- 日期：2026-09-20
- 实例 / 卡型：AutoDL A800 80GB（无卡模式完成全部数据准备后切换）
- 一句话目标：Qwen2.5-Coder-3B-Instruct 零样本在双闸评估集上的基线

## 配置

| 项 | 值 |
|---|---|
| 模型 | Qwen2.5-Coder-3B-Instruct（ModelScope 下载，实例已有） |
| 训练方式 | 无（零样本） |
| 训练数据 | — |
| 评估集 | 自建 10 题（eval split）+ VerilogEval V2 清洗后 36 题 = **46 题** |
| 采样方式 | 贪心解码 n=1（pass@1），max_new_tokens 1024，</answer> 停词 |
| 工具链 | Yosys 0.9 + Verilator 4.038（apt 安装；harness 不依赖 -j/--timing） |

## 命令

```bash
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    data/verilogeval_cleaned.jsonl \
    --model /root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct \
    --split eval --out-dir results/e1
```

## 跑分

| 指标 | 值 |
|---|---|
| **pass@1（双闸全过）** | **0.3696（17/46）** |
| 综合通过率 | 0.9130 |
| 仿真通过率 | 0.3696 |
| 仿真通过率（综合过者中） | 0.4048 |
| 格式达标率 | 1.0000 |

分档：combinational 0.2812（32 题）/ sequential **0.6667**（12 题）/ fsm **0.0000**（2 题）

失败原因分布：verilator_compile_error(cand) 14（候选真编译错）/ synth_fail 4 /
gold_oracle_mismatch 5（与参考行为不一致）/ 测试向量不匹配 2（自建题）/ 其余综合过+仿真部分过

## 作废记录（诚实纪律，显式标注）

- **第一轮 E1 数字（pass@1 = 0.0652）作废**。原因：`run_gold_oracle` 的 verilator
  命令残留 `-j2`（Verilator 4.038 不支持，编译全挂），36 道 VerilogEval 题的候选
  全部假失败。修复 + 源码级防回归断言（selftest 检查 -j2 不再出现）后重跑，
  0.3696 为有效数字。
- 数据准备期修复的测试向量 bug（BCD 非法输入/LFSR 周期/clkdiv10 错位/边沿检测
  复位语义）不影响 E1 数字（在 --verify 阶段已修）。

## 坑

1. Verilator 4.038 无 -j / 无 --timing —— harness 只用基础特性，命令不传 -j；
   WIDTH 等 lint 警告会致命 → 统一加 -Wno-fatal（闸门②判功能不判 lint）
2. hf-mirror 上传 Xet 后端挂死 → HF_HUB_DISABLE_XET=1 走 LFS/S3
3. AutoDL 后台命令会杀 SSH 通道（进程照常跑）——查进程用 pgrep，勿重复启动
4. VerilogEval 旧 JSON 已不存在（2024-08 改版）→ 用 V2 spec-to-rtl 目录格式
   （jsdelivr CDN 下载 156 题，46 题因可综合性/位宽/重复被清洗剔除）
5. 无 rst 端口的时序题 oracle 测试构造出 None 键 → 已修 + 防御检查

## 花费与耗时

- 数据准备（无卡模式）：≈ ¥0.3 | E1 评估：~30 分钟 GPU 卡时 ≈ ¥3

## 下一步

- E1 基线高于设计文档预期（37% vs「可能极低」）：Qwen2.5-Coder 本就训练过
  Verilog。叙事调整为「零样本综合率 91% 但功能率 37%——语法会了、逻辑不会」。
- FSM 0% 是训练信号的最大机会点。进 E2（SFT）。
