# RTL-RLVR 教程骨架（开源时填充；GitHub 习惯：结论文档 + 教程 + 踩坑手册）

> 结构照两个老项目（search-r1-repro / code-r1-repro 的 TUTORIAL）。E1-E3 跑完
> 后把数字填进占位符即可发布。

---

## 0. 这是什么（30 秒版）

用「Yosys 综合 + Verilator 仿真」当天然可验证奖励，在 RTL（Verilog）域复现
RLVR 管线——VeriRL 的 mini 复现。一句话卖点：**RTL 的奖励比软件代码更干净——
仿真没有运行时不确定性，RLVR 的完美落地场景。**

## 1. 背景与方法（面试叙事同款）

| Code-R1（软件） | RTL-RLVR（硬件） |
|---|---|
| 题目 → Python | spec → Verilog module |
| ast.parse 编译 | Yosys 综合 |
| 沙箱跑测试 | Verilator 仿真（自动生成 C++ harness） |
| 奖励 = 格式 0.1 + 正确 1.0 | 同构（满分 1.1） |
| 1.5B verifier 预测 k/N | RTL verifier（E4 可选） |

## 2. 数据

- 自建 50 题 spec 集（组合 20 / 时序 20 / 状态机 10；含参考实现 + 测试向量；
  参考实现全部通过自身双闸自检——数据集的诚信底线）
- [VerilogEval 143 题清洗（若用了）]
- 统一 jsonl 字段：spec / header / module / tests / tier / split

## 3. 训练

- E2：LLaMA-Factory LoRA(32/64) SFT，3 epochs
- E3：veRL GRPO（n=4, kl=0.001, lr=1e-6, 50 步），reward_fn 只改双闸
- 奖励明细表（-0.1 / 0.1 / 1.1 语义 + 可选开关）

## 4. 结果

| 实验 | pass@1 | 综合率 | 仿真率 | 格式率 |
|---|---|---|---|---|
| E1 零样本 | | | | |
| E2 SFT | | | | |
| E3 GRPO | | | | |

结论三段式（事实/机制/叙事）+ 负面结果如实报告（照 docs/结论文档模板.md 第七节）。

## 5. 如何复现（最小闭环，半天）

```bash
sudo apt install -y yosys verilator build-essential
python scripts/build_spec_set.py --verify      # 数据自检
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    --model <你的模型> --split eval --out-dir results/e1   # 任何 HF 模型都能评
```

## 6. 踩坑手册（发布时从 work-log 汇总）

- （预计素材：verilator 编译是奖励计算大头、chat 模板系统提示词一致性、
  接口不一致 = 仿真闸判失败的口径、镜像克隆 torch 损坏……）
