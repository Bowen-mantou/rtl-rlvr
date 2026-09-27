# RTL-RLVR 操作手册（RUNBOOK）

> 你只做三件事：租卡 → 复制粘贴命令 → 把结果粘回来。每节给出「预期输出」，
> 对不上就停下，把命令 + 输出一起粘回来。**硬截止：2026-09-22 周二中午训练全部跑完。**

- [0. 总览与预算](#0-总览与预算)
- [1. 租卡与上传](#1-租卡与上传)
- [2. 环境与工具](#2-环境与工具)
- [3. 数据准备（第一步先做）](#3-数据准备第一步先做)
- [4. E1 基线评估](#4-e1-基线评估)
- [5. E2 SFT](#5-e2-sft)
- [6. E3 GRPO](#6-e3-grpo)
- [7. E4 verifier（可选）](#7-e4-verifier可选)
- [8. 收尾与粘回](#8-收尾与粘回)

---

## 0. 总览与预算

| 实验 | 内容 | 预计耗时 | 预算 |
|---|---|---|---|
| E1 | Qwen2.5-Coder-3B-Instruct 零样本基线 | 评估 ~20 分钟 | 含在卡时里 |
| E2 | E1 + LoRA SFT（LLaMA-Factory） | 训练 ~15 分钟 | ≈ ¥5 |
| E3 | E2 + GRPO 双闸奖励（veRL，50 步） | 训练 2-4 小时 | ≈ ¥20-30 |
| E4 | E3 + verifier 软信号（可选） | 2-3 小时 | ≈ ¥10 |

总预算 ¥70-100。**推荐租卡方案：直接重启 Code-R1 的 6000D-84G 实例**（veRL 环境、
Qwen2.5-Coder-3B 模型、convert_ckpt.py 全都在，省掉全部环境搭建时间）。

路径约定（本手册全部用绝对路径，不用改）：

| 本地（本文件夹） | 远程（实例） |
|---|---|
| 项目根 `05-rtl-rlvr/` | `/root/autodl-tmp/rtl-rlvr/` |
| `data/` `results/` `logs/` | `/root/autodl-tmp/rtl-rlvr/{data,results,logs}/` |
| 模型目录（脚本里写的） | `/root/autodl-tmp/models/` |

若你的实例路径不同（比如项目放 `/root/rtl-rlvr`），全局替换：
`sed -i 's#/root/autodl-tmp/rtl-rlvr#你的路径#g'` 各 yaml/json/命令里的路径即可；
各 python 脚本内部路径全部是**相对项目根**的，不用改。

---

## 1. 租卡与上传

1. AutoDL 控制台 → 选 Code-R1 用过的实例（6000D-84G，¥5.98/h）→ 开机。
   若该实例已释放：租同配置新实例，装环境走 §2 的「路径 B」。
2. **上传本项目**（三选一）：
   - 最简单：控制台「文件管理 / JupyterLab」上传本文件夹的 zip（排除 `results/`
     里的大文件；`data/grpo/*.parquet` 已生成好，要一起传）。
   - SCP：`scp -P <端口> -r 05-rtl-rlvr root@<主机>:/root/autodl-tmp/`
   - 你熟悉的 run_ssh.py 双层 base64 上传（老项目方法）。
3. 上传后解压到 `/root/autodl-tmp/rtl-rlvr`，检查文件齐：
   ```bash
   cd /root/autodl-tmp/rtl-rlvr && ls scripts configs data docs
   ```
   预期看到：`rtl_common.py build_spec_set.py eval_rtl.py clean_data.py ...` 和
   `data/spec_set_50.jsonl data/grpo/train.parquet`。
4. ⚠ **不要在 Windows 上编辑 .sh 文件再传**（CRLF 会炸 bash，老坑）。传上去的
   文件直接跑。

## 2. 环境与工具

**路径 A（推荐）：复用 Code-R1 实例**——veRL 环境已配好，只补 RTL 工具：

```bash
# ① 验证旧环境还在（缺哪个装哪个，输出异常就粘回来）
python -c "import torch, vllm; print('torch', torch.__version__)"
python -c "import verl; print('verl ok')"
# ② RTL 工具链（一条命令，AutoDL 自带 apt 源）
sudo apt install -y yosys verilator build-essential
# ③ 验证（应输出各自版本号）
yosys -V && verilator --version && make --version | head -1
```

**路径 B：全新实例**（租不到旧实例时）——按 03-code-r1/docs/PITFALLS.md 重建
veRL main 环境（锁旧实例同款 commit：`git clone` 后 `git log` 对比实例上的
`/root/autodl-tmp/verl`），再装 LLaMA-Factory 独立 conda 环境（§5）。这是慢路径，
预算多算 ¥10-15。

**模型下载（ModelScope 优先；复用 Code-R1 实例可跳过 Coder-3B，它已在
`/root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct`）**：

```bash
pip install modelscope --index-url https://pypi.tuna.tsinghua.edu.cn/simple
modelscope download --model Qwen/Qwen2.5-Coder-3B-Instruct \
    --local_dir /root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct
# 仅 E4 需要（1.5B verifier 基座）：
modelscope download --model Qwen/Qwen2.5-1.5B-Instruct \
    --local_dir /root/autodl-tmp/models/Qwen2.5-1.5B-Instruct
```

---

## 3. 数据准备（第一步先做）

```bash
cd /root/autodl-tmp/rtl-rlvr
mkdir -p logs results data/raw data/sft data/verifier

# 3.1 静态检查（不调工具，秒级）
python scripts/eval_rtl.py dry-run --problems data/spec_set_50.jsonl --split eval
# 预期: [dry-run] 题库 10 题校验通过 ... OK —— 配置/路径/文件全部就位

# 3.2 ★ 数据集诚信自检：50 题参考实现必须全部通过自己的双闸
python scripts/build_spec_set.py --verify
# 预期: 50 行 [PASS] + 最后一行 ✅ 50 题参考实现全部通过双闸自检。可以开训。
# 有任何 [FAIL] → 把输出粘回来（数据集本身有 bug，禁止开训，等修复）

# 3.3 VerilogEval V2（jsdelivr CDN，~2 分钟；已完成过可跳过下载直接清洗）
python scripts/clean_data.py --download-v2 data/raw/verilogeval_v2
python scripts/clean_data.py --input-v2 data/raw/verilogeval_v2 \
    --out data/verilogeval_cleaned.jsonl --eval-n 40 --annotate
# 预期: [clean] 总计 98 题（156 题中：46 题参考实现过不了 Yosys 0.9 被剔除
#       ——V2 Human 解答含 SystemVerilog 特性；11 题端口超 64 位；1 题重复；
#       这是真实的「可综合性过滤」数据清洗，面试可讲）
# 网络不通就跳过 3.3：主线（E1-E3）只用自建 50 题也能跑，work-log 注明即可

# 3.4 GRPO 数据（已生成好并随项目上传：94 train + 8 val；3.3 重做才需重生成）
python scripts/make_grpo_parquet.py --problems data/spec_set_50.jsonl \
    data/verilogeval_cleaned.jsonl --split train --val-n 8 --out-dir data/grpo
```

## 4. E1 基线评估

```bash
cd /root/autodl-tmp/rtl-rlvr
# 评估集 = 自建 10 题 + VerilogEval V2 清洗后 36 题 = 46 题（--problems 多文件）：
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    data/verilogeval_cleaned.jsonl \
    --model /root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct \
    --split eval --out-dir results/e1
# 预期: [generate] 加载模型... 46 题×1 采样 → [eval] pass@1 = 0.xxxx
#       （可能极低，设计文档第十一节说过：E1 低反而强化「SFT 教格式」对比，如实记录）
```

产物：`results/e1/report.md` + `report.json`。**粘回**：report.md 全文 + 日志里的
pass@1 一行。同时复制一份 work-log（模板在 `docs/work-log-模板.md`）填 E1 节。
⚠ 口径纪律：E1 用哪条命令（几个文件），E2/E3 必须用完全相同的命令（同一评估集）。

## 5. E2 SFT

```bash
# 5.1 数据（已随项目生成好，可选并入 VerilogEval）
cd /root/autodl-tmp/rtl-rlvr
python scripts/to_llamafactory.py --problems data/spec_set_50.jsonl \
    data/verilogeval_cleaned.jsonl --split train --out data/sft/sft_alpaca.json

# 5.2 装 LLaMA-Factory（独立 conda 环境，~10 分钟）—— 完整命令见
#     configs/sft/命令清单.md，照抄第 2-3 步（安装 + 注册数据集）

# 5.3 训练 + 合并 + 评估（命令清单第 4-6 步）
# 预期: 训练 5-15 分钟（40-143 条 × 3 epochs）；合并出 /root/autodl-tmp/models/e2-sft-merged
#       E2 评估 report.md 里「格式达标率」应明显高于 E1（SFT 学格式的量化证据）
```

## 6. E3 GRPO

**⚠ 启动前检查清单（2026-09-20 事故教训，必做，30 秒）**：
1. **初始权重指向**：`grep MODEL_PATH configs/grpo/run_grpo.sh` 必须是
   `/root/autodl-tmp/models/e2-sft-merged`（E3 = E2 + GRPO；曾误指原始基座
   白跑 36 步才在复盘时发现——run_grpo.sh 已加存在性断言，但指向是否正确
   只有人能核对：错误路径也「存在」，断言拦不住）
2. **磁盘空间**：`df -h /root/autodl-tmp` 可用 > 30G（checkpoint 轮转在本版
   veRL 实测不生效，靠 ckpt_watchdog.sh 兜底；训练前确认 watchdog 在跑：
   `pgrep -f ckpt_watchdog`）
3. **数据**：`data/grpo/train.parquet` 行数 = 94（prompt 列必须是消息列表
   格式，reward_model 列必须是 struct——两个都是踩过的坑）

```bash
cd /root/autodl-tmp/rtl-rlvr
# 6.1 干跑配置断言（PITFALLS 纪律：启动前 dry-run）
python scripts/eval_rtl.py dry-run --problems data/spec_set_50.jsonl --split eval

# 6.2 启动（必须从数据盘 cwd 启动！checkpoint 位置由 cwd 决定，老坑）
cd /root/autodl-tmp
nohup bash rtl-rlvr/configs/grpo/run_grpo.sh > rtl-rlvr/logs/e3_train.log 2>&1 < /dev/null &
# 后台化注意：单独一条命令 + < /dev/null（老坑）；重发启动前先 pgrep 查进程：
pgrep -f main_pp[o] || echo "no verl process"

# 6.3 监控（另开终端）
tail -f /root/autodl-tmp/rtl-rlvr/logs/e3_train.log
# 预期: 前 2 分钟出现 vLLM 启动 + 第一个 step 的 reward 打印；step 间隔约 1-3 分钟
#       （verilator 编译是奖励计算大头，慢是正常的）
# 可复用 Code-R1 实例上的 remote_watchdog_run.sh 做崩溃监控（可选）

# 6.4 训练完（50 步，约 2-4 小时）→ 转 bf16 模型
ls /root/autodl-tmp/checkpoints/rtl-rlvr/e3-grpo-dualgate-3b/global_step_*/actor/
# 取最后一个 global_step_XX（不要 final 目录里没写完的）
python rtl-rlvr/scripts/convert_verl_ckpt.py \
    --ckpt /root/autodl-tmp/checkpoints/rtl-rlvr/e3-grpo-dualgate-3b/global_step_50/actor/model_world_size_1_rank_0.pt \
    --src-model /root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct \
    --dst /root/autodl-tmp/models/e3-final-3b

# 6.5 E3 评估（与 E1/E2 同一脚本同一采样、同一评估集命令）
cd /root/autodl-tmp/rtl-rlvr
python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
    data/verilogeval_cleaned.jsonl \
    --model /root/autodl-tmp/models/e3-final-3b --split eval --out-dir results/e3
```

可选变体（时间够才跑，E 系列单独验证；命令行末尾追加）：
- E3b 拆两段奖励：`+reward.custom_reward_function.reward_kwargs.split_reward=True`
- E3c lint 行为奖励：`+reward.custom_reward_function.reward_kwargs.lint_bonus=True`

步数账（默认已配好）：94 题 train / batch 8 ≈ 12 步/epoch × 6 epochs = 72 步
（50-100 红线内）。只用自建 40 题时改 `trainer.total_epochs=10`（50 步）。

## 7. E4 verifier（可选）

照 `configs/verifier/命令清单.md`：标注 → 训练 → 校准（ECE<0.05 验收）。
主线 E1-E3 没跑完前不要碰 E4。

## 8. 收尾与粘回

1. **核对数字**（设计文档第八节：所有数字入表前核对两遍）：
   `results/e1/report.json` 里的 aggregates 与 report.md 表逐项对一遍。
2. **粘回内容**（每个实验）：
   - work-log（按 `docs/work-log-模板.md` 填：配置/命令/跑分/坑）
   - `results/eX/report.md` 全文
   - 训练日志的关键段（reward 前几 step + 最后几 step；`logs/e3_train.log` 尾 200 行）
3. **关机省钱**（PITFALLS：容器内要用 `/usr/bin/shutdown`，不是 `/usr/sbin/shutdown`）：
   ```bash
   /usr/bin/shutdown
   ```
4. AI 侧拿到结果后填 `docs/结论文档模板.md` 出对比表 → 简历加一行。

---

## 常见坑速查（全部来自前两个项目实踩）

| 现象 | 处理 |
|---|---|
| `verilator` 编译报缺 gcc/make | `sudo apt install -y build-essential` 后重跑 |
| yosys/verilator 不存在 | 没跑 §2 第 ② 步 |
| `--verify` 有 FAIL | 数据有 bug，粘回输出，等修复，禁止开训 |
| 训练 ckpt 写到系统盘 / 磁盘满 | 启动时 cwd 不是 `/root/autodl-tmp`（§6.2 红线） |
| vLLM EngineCore 报 libcudart/libnvrtc | 6000D 实例缺 cu13 库路径（run_grpo.sh 已带，别删） |
| 进程双开写同一 checkpoint | 启动前先 `pgrep -f main_pp[o]` 查（PITFALLS 老坑） |
| 后台命令 SSH 挂起 | 启动命令已带 `< /dev/null`；超时≠没跑，先 pgrep |
| reward 全部 -0.1 | 模型没输出 `<answer>` 标签 —— E1 零样本正常现象；训练中持续出现则查 prompt 是否被截断（max_prompt_length 1024） |
| 单步训练 >10 分钟 | verilator 编译慢 + 并发不足；确认机器空闲核数，别和评估抢 CPU |
| 评估集划分 | **禁止按 task_id 编号取前 N**（2026-09-21 教训：VerilogEval V2 按编号难度排序，取前 40 = 全是最简单题，数字虚高 2 倍）——用随机分层抽样，分层数字（简单/难题 split）必须分开报 |
