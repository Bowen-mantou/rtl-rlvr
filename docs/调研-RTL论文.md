# 调研：RTL/Verilog 代码生成的论文谱系与我们的定位（2026-09-21）

## 一、谱系速览（按方法演进）

| 工作 | 年份 | 路线 | 关键设计 | 与我们的对应 |
|---|---|---|---|---|
| RTLCoder | 2023/24 | SFT | GPT 生成 27K 指令-代码对（关键词树→指令→代码）；纯语法检查 | E5 teacher 蒸馏的 mini 版（我们多了双闸功能过滤） |
| VeriCoder | 2025 | SFT | 反馈驱动精化：teacher 迭代生成设计+单测直到仿真过 → 125K 功能验证三元组；消融证实「验证过的数据 > 没验证的」 | **我们 E5/E6 的核心理由**（双闸 = 功能验证；151 条 vs 125K 的 mini 版） |
| **VeriRL** | 2025 | **迭代 RL** | 7B Qwen2.5-Coder 四阶段：cold-start SFT → RL（Reinforce++ + SbW）→ rejection sampling 39K → SFT → RL；训练 reward model 打分（Trace-back Rescore）；**SbW 防灾难遗忘/过拟合** | 我们 E1-E3+E6 的完整版；我们 66 步早停 ≈ 论文 SbW 要解决的问题 |
| VeriReason | 2025 | SFT+GRPO | 奖励 = 语法 + testbench 功能 + AST 结构相似度（2.0/0.1+AST 分）；iverilog testbench；VerilogEval-Machine 83.1% pass@5 | 与 P0 配方轴同构；其 AST 相似度 soft 项 ≈ 我们证伪的 split 奖励（他们留了，我们证伪了——有趣的对照） |
| **VeriPrefer** | 2025 | SFT→DPO | 自动 testbench 生成管线 + VCS 反馈 → 基于 testbench 结果的偏好对 → DPO；消融：**「SFT with verified data does not match RL gains」** | **与 E7 完全同构**；直接背书 DPO 在数据轴之后的排序 |
| VeriContaminated | 2025 | 评测 | 检测确认 VerilogEval/RTLLM 可能污染训练语料 | 我们「同分布内评估」诚实标注的论文级依据 |

## 二、三个直接影响我们结论的发现

1. **VeriRL 的 SbW（sample-balanced weighting）**：动态按奖励-概率分布平衡梯度，
   防 RL 阶段灾难遗忘/过拟合——我们 132 步过拟合的论文级解法（我们用了
   「66 步早停」的朴素版；面试可讲两者的 trade-off）
2. **VeriReason 的奖励设计**：功能 2.0 / 语法 0.1+AST 相似度——「过程 soft 项」
   与我们的 split_reward 同族，但我们实测证伪了它（五格全负）——**小数据下
   soft 过程奖励有害，是我们的实证贡献点，与论文结论形成对照**
3. **VeriPrefer 的消融**：「已验证数据的 SFT 不如 RL 增益」——支撑我们把
   E6（自举 SFT）排主路线、E7（DPO）排在最后的顺序决策

## 三、我们的定位（面试 30 秒版）

「VeriRL/VeriReason 的 mini 复现 + 三轴消融深化。独特贡献四点：
① 纯规则双闸奖励（Yosys+Verilator），不需要论文里的 reward model 训练——
奖励更硬、管线更短；② 难度分层诊断（V2 按编号难度排序的发现）让全部结论
按简单/难题 split 报告；③ 三轴消融矩阵（数据源/奖励配方/训练顺序）在 3B
小模型 + 102 题小数据上给出可复现结论：split 奖励证伪、组过滤难题 +5.2pp、
66 步最优停止；④ 小数据过拟合的实证与早停策略。」

## 四、论文留给我们的差距（诚实报告）

- VeriRL 的数据规模（Veribench-53K/39K rejection samples）是我们的 ~300 倍；
  我们的绝对数字不具可比性，结论的价值在「方法链路 + 消融洞察」
- 判分口径：VeriReason/VeriPrefer 用 iverilog/VCS 真 testbench；我们用
  双闸 + 参考 oracle（VerilogEval 题）——判分精度弱一档，已如实标注
- 未实现论文级组件：SbW、trace-back rescore、testbench 自动生成——每个都
  可作为后续工作点

## 五、四篇论文逐一指导 + 我们的改进动作（含成本/优先级）

### RTLCoder（数据生成模板化）
- 指导：关键词树 → 指令 → 代码的分层生成，把数据多样性做成显式流程
- 我们的改进（**P1，低本钱**）：E5 teacher 采样的多样性不够（151 条正样本里
  95 条与参考实现重复 = 简单题标准答案唯一，但也说明生成多样性低）。
  用关键词扩展 spec 变体（如「8-bit adder」→ 变进位宽/接口风格/约束条件），
  teacher 再采样一轮，正样本池可扩 ~2 倍
- 成本：API ¥2-3 + 2 小时

### VeriCoder（反馈驱动精化）
- 指导：teacher 生成 → 仿真失败 → 带错误信息修复 → 直到过——把「验证」做成
  「生成循环」；核心消融：**功能验证过的数据 > 没验证的**
- 我们的改进（**P0，直接对口**）：teacher 采样里「综合过仿真错」的 ~120 条
  轨迹是现成的修复素材——把失败样本 + 错误信息回喂 DeepSeek 迭代修复一轮，
  通过率 60.3% 预期推到 ~80%，正样本 151 → ~250 条。这正是 VeriCoder 反馈
  驱动精化的 mini 版，管线（采样→双闸→回喂）全部现成
- 成本：API ¥2-3 + 2 小时

### VeriRL（四阶段迭代 RL + 防遗忘）
- 指导：SbW（样本平衡加权）防灾难遗忘；rejection sampling 固化 RL 能力
- 我们的状态：四阶段已做三阶段半（E2/E3/E6/最终 GRPO）；66 步早停 = SbW 的
  朴素替代
- 改进候选（**P2，标「设计就绪」**）：SbW 简易版（按难度加权梯度）——小数据
  下效果未知，面试可讲「我用早停，论文用加权，两者是同一问题的两种解法，
  加权在我的数据规模下优先级低」

### ChatSVA（多 agent 任务分解 + 数据验证闭环）
- 指导：Spec→验证计划→特征→检查点→SVA 的四段分解把难题切成子任务；
  AgentBridge 三原则（信息方向性约束 / 金标准溯源 / 输出可验证）——
  我们双闸 = 确定性验证，纯度 100%（ChatSVA 用 5 验证者投票才到 99.9%，
  我们是单验证者 100%，样本少但判定硬）
- 改进候选（**P2，高价值但大改**）：难题的「结构化提示」——把复杂时序/FSM
  spec 重写成「接口+状态转移表+行为描述」的中间表示（类似 Verification
  Plan），给模型一个更细的生成任务。62 道难题 × 结构化重写 ≈ 3-4 小时，
  收益未验证，列为面试后续工作点
- 一句话：我们做了 ChatSVA 的「输出可验证」半边（双闸），没做「任务分解」
  半边——难题 14.5% 的低分正是缺这半边的代价

## 来源

- [ChatSVA (arXiv:2604.02811)](https://ar5iv.labs.arxiv.org/html/2604.02811)
- [VeriRL: Boosting the LLM-based Verilog Code Generation via RL (arXiv:2508.18462)](https://ar5iv.labs.arxiv.org/html/2508.18462)
- [VeriReason: RL with Testbench Feedback (arXiv:2505.11849)](https://www.semanticscholar.org/reader/afe52867528e35d6469fe38febfe7ba7788b8a85)
- [VeriCoder: Enhancing LLM-Based RTL Code Generation (arXiv:2504.15659)](https://ar5iv.labs.arxiv.org/html/2504.15659)
- [RTLCoder (arXiv:2312.08617)](https://arxiv-org.ezproxy.obspm.fr/html/2312.08617v5)
- [VeriPrefer / Insights from Verification: Training Verilog LLM with RL and Testbench Feedback (arXiv:2504.15804)](https://export.arxiv.org/pdf/2504.15804)
- [VeriContaminated (arXiv:2503.13572)](https://arxiv.org/pdf/2503.13572)
