# 文献调研：RTL-LLM 后训练方法（2026-09-21 检索）

> 目的：给 P0/E5/E6/E7 实验计划找文献依据，回答「这方面别人怎么做」。检索源：VeriRL（arXiv 2508.18462）、VeriCoder（arXiv 2504.15659）、RTLCoder（arXiv 2312.08617）、VeriReason（2026）等。

## 一、四篇核心论文方法速览

### RTLCoder（2023，SFT 路线开山）
- **三阶段自动化数据生成**：关键词池（keyword pooling）+ 分层提示词（hierarchical prompt）从 GitHub 公开代码生成 **RTLCoder-27K** instruction-code 对
- 7B 模型 SFT 后 VerilogEval v1 machine ≈ 62.5%，超过 GPT-4 的 60%
- **局限（VeriCoder 测出）**：RTLCoder-27K 里只有 **24.4%** 的样本能通过功能测试——语法对但功能错的脏数据占比高

### VeriCoder（2025，功能验证驱动的数据合成）
- 方法：**单元测试生成 + 反馈驱动精炼（feedback-directed refinement）**——给每个 spec 生成测试，用测试结果迭代精炼代码，训练集全部经过功能验证
- 核心发现：**功能验证过的数据训练效果显著优于只验证语法的数据**（对照：RTLCoder 24.4%、OriGen 53.5% 的功能通过率）
- 14B 模型 VerilogEval v2 machine ≈ 60%+

### VeriRL（2025，RL 路线）
- **数据**：Veribench-53K（从 700K 问题筛出），每题 **5-10 个多样化 testbench**（边界敏感性/时序/功能）
- **Trace-back Rescore（TbR）**：错样本不直接丢——按 testbench 通过率选择性扩展，对「语义有意义但语法有缺陷」的样本回溯推理路径、重新采样、重新打分，改善偏好数据质量
- **Sample-balanced weighting**：按 reward-probability 分布自适应平衡样本权重——缓解 RL 微调的**灾难性遗忘和过拟合**
- 迭代 RL 管线：策略模型与奖励模型共同进化（co-evolve）
- 论文原话：CraftRTL 靠大规模闭源模型蒸馏（另一条被承认的路线）；DeepSeek 式纯 GRPO 在稀疏反馈上挣扎——**正是我们 P0 要解决的诊断**

### VeriReason（2026）
- **SFT + GRPO-based RL + testbench feedback**——和我们 E2/P0+E3 的结构几乎一致（我们的路线与 2026 最新工作对齐）

## 二、对本项目的启示对照表

| 文献做法 | 我们的对应 | 差距/可抄的点 |
|---|---|---|
| VeriCoder：功能验证过滤数据 | 双闸过滤（综合+仿真） | ✅ 方向一致——我们的过滤就是「feedback-directed refinement」的 mini 版，面试可直接对齐 |
| VeriRL TbR：错样本回溯重采样重打分 | E7 构对规则（通过 vs 综合过仿真错） | 我们的构对是 TbR 的简化版；升级版 = 对「低通过率样本」生成多条推理路径重打分——写进 E7 改进方向 |
| VeriRL sample-balanced weighting | （被否决的）难题固定过采样 | ✅ 印证否决正确：文献解法是「reward 分布驱动的动态权重」不是固定过采样——写进结论的改进方向 |
| Veribench：每题 5-10 个多样 testbench | 自建集每题 1 套测试向量 | 扩池方向：模型生成多样 testbench + 双闸验证 gold——数据工程下一步 |
| CraftRTL：大规模闭源模型蒸馏 | E5 DeepSeek API 蒸馏 | ✅ 文献承认的路线，E5 合理；我们是 CraftRTL 路线的 mini 版 |
| VeriRL：奖励模型共同进化 | P0 split_reward（信号消融） | 两条解稀疏信号的路：我们走「拆段客观信号」，VeriRL 走「TbR + 奖励模型」——面试可对比着讲 |
| VeriReason：SFT + GRPO + testbench 反馈 | E2 + P0/E3 | ✅ 结构与 2026 最新工作一致，且我们多了 P0 信号消融这个独有实验 |

## 三、可立即落地的改进（按优先级）

1. **E7 构对升级（低成本）**：把「通过 vs 综合过仿真错」升级为 TbR 简化版——对「低通过率样本」让模型多采样几条推理路径，取最好的一条当 chosen 候选；数据量不变、构对质量升
2. **结论改进方向加一条（零成本）**：sample-balanced weighting 替代被否决的固定过采样——「reward 分布驱动的动态权重」作为 P1 改进项写进结论文档
3. **面试叙事升级（零成本）**：「我们的双闸过滤就是 VeriCoder 反馈驱动精炼的 mini 版；E5 蒸馏对应 CraftRTL 路线；P0 信号消融和 VeriRL 的 TbR 是解稀疏信号的两条互补路径；整体结构与 VeriReason 对齐——四篇前沿论文每条都有我们的对应实验」

## 四、面试口径（文献对照版）

被问「你的方法和论文什么关系」：「我的 E2 用的是功能验证过的数据——这正是 VeriCoder 的核心发现（功能验证数据优于语法验证数据，公开数据的脏率 RTLCoder 只有 24.4% 功能通过）；GRPO 信号稀疏是 VeriRL 论文点名的问题，我的 P0 消融用拆段客观信号解、他们用 TbR 加奖励模型解；E5 蒸馏对应 CraftRTL 承认的闭源蒸馏路线。我的 mini 项目相当于把四篇论文的核心路线各做了一个对照格。」
