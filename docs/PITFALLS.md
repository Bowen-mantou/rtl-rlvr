# RTL-RLVR 踩坑手册

> 每条都是本项目（2026-09-20/21 两天）真实踩过、定位过、修复过的。
> 按类别整理，供复现者与后续项目参考。

## 一、veRL 数据契约（每条都导致过训练崩溃或假训练）

| 坑 | 正确做法 |
|---|---|
| `reward_model` 列存 JSON 字符串 → veRL 取 `["ground_truth"]` 时 TypeError | 必须是 **dict**：`{"style": "rule", "ground_truth": "<json str>"}` |
| `prompt` 列预格式化 chat 模板字符串 → 被 Jinja 当字符流迭代，只剩 24 token 模板骨架，全部 reward -0.1 假训练 | prompt 列必须是**消息列表**：`[{"role": "user", "content": ...}]`，模板交给 veRL 套 |
| `algorithm.filter_groups.metric=score` 崩溃「missing DAPO metric」 | 本版 veRL 对 float 返回自动写 `reward_extra_info["acc"]`，**metric 用 `acc`** |

## 二、veRL checkpoint 与磁盘（三次写满 62G 磁盘的教训）

| 坑 | 正确做法 |
|---|---|
| `max_actor_ckpt_to_keep=1` 实测不生效，13G/份的 checkpoint 堆积写爆磁盘，torch.save 崩溃（`inline_container.cc unexpected pos`） | 外部 **ckpt_watchdog** 兜底：每 2 分钟只保留最新目录；带 mtime 保护（最新目录还在写入时跳过清理） |
| 训练前不查磁盘 → 启动即埋下崩溃种子 | **训练前必查 `df -h`**：峰值 = 基础占用 + 2×13G（旧 ckpt + 新 ckpt 保存重叠） |
| 保存瞬间写满 → ckpt 半成品（如 951M 残档） | 崩溃后先删残档；磁盘允许时优先从最近**完整** ckpt 续训 |
| 无卡模式 2GB 内存限制，torch.load 大模型必被 kill | 转换/加载大模型必须在 GPU 模式做；无卡只做轻 CPU 任务 |

## 三、训练配置与口径

| 坑 | 正确做法 |
|---|---|
| **初始化契约**：E3 曾误指原始基座而非 SFT 模型，白跑 36 步才在复盘发现 | run 脚本加存在性断言 + 启动前**人核清单**（断言拦不住「指向错误的模型」） |
| 66 步最优、132 步过拟合（训练 reward 涨、泛化崩） | 小数据 GRPO 早停 + 盯未见题口径，别只看训练 reward |
| split_reward（综合 0.3/仿真 0.7）全口径落败 | 「综合过仿真错」被抬成合格样本，削弱功能信号——二值优于分档（本项目证伪结论） |
| DAPO 组过滤的副作用：简单题「全对组」被滤 → 能力退化 | 难题特化配方 vs 均衡配方的 trade-off 要分层报告 |
| **评估集划分按编号取前 N**：VerilogEval V2 按编号难度排序，取前 40 = 全是最简单题，数字虚高 2 倍 | 随机分层抽样；**未见题口径做主判据**，训练题口径必须标注「分布内」 |
| 训练题成绩误报成模型能力（62 道训练题混进「全集」口径） | 报告头条 = 未见题；两条口径并列且明确标注含义 |

## 四、AutoDL 运维

| 坑 | 正确做法 |
|---|---|
| 后台命令启动会杀 SSH 通道（命令可能没执行） | 启动后立即 pgrep 查远端进程；「超时 ≠ 没跑」 |
| 链式脚本与手动并行启动打架 → 双进程写同一文件损坏 | 重启前先 pgrep 查活进程；链式脚本与手动启动二选一 |
| `pkill -f xxx` 匹配自身命令行自杀 | 用 `pkill -f 'main_pp[o]'` 方括号技巧 |
| 数据盘 100% 满导致各种诡异崩溃（quota exceeded / zip write 错位） | 每次启动训练前 df 检查；删冗余模型有决策清单（结果已记录的才删） |
| 镜像克隆后环境损坏、装包降级 torch（flashinfer 红线） | 不装 flashinfer；装包后验证 `torch.__version__` |
| 上传文件失败「chunk 1/N」 | 先确认远端目录存在（upload 预置 touch 失败）；大文件按行 split 上传 |

## 五、网络与镜像（国内环境）

| 坑 | 正确做法 |
|---|---|
| HF 直连被重置 / GitHub 直连不通 | gh-proxy（raw 文件）、jsdelivr API（列目录）、hf-mirror（下载）；push 走 127.0.0.1:7897 |
| hf-mirror 上传大文件挂死 | `HF_HUB_DISABLE_XET=1` 走 LFS/S3；速度不稳时保持断点重试 |
| gh-proxy git clone 极慢 | codeload tarball 单文件下载替代 |
| PyPI 上无 llamafactory 包；清华源部分包 403；阿里云 av 轮子固定卡死 | venv + `--system-site-packages` 复用 torch + 双镜像 + aria2 多连接拉问题轮子 |
| .condarc 里清华 pkgs/free 频道已废弃 | venv 方案绕开 conda |

## 六、代码与工具

| 坑 | 正确做法 |
|---|---|
| Verilator 4.038（Ubuntu 22.04 apt）：无 `-j`、`--timing`；WIDTH 警告会致命 | harness 只用基础特性；命令统一 `-Wno-fatal`；源码级 selftest 防 `-j2` 回归 |
| .sh 被 Windows Python 重写产生 CRLF → `pipefail: invalid option` | 改 .sh 只用 Write/Edit 工具（LF）；上传后 file 检查 |
| harness 生成的 C++ 里 printf 格式串尾部逗号 / 实参尾逗号 | 生成代码也要过编译（--verify 阶段兜底） |
| 测试向量期望值笔误（BCD 非法输入、LFSR 周期末拍、非阻塞语义差一拍） | 参考实现先过自身双闸（--verify）才入库；期望值用 Python 镜像仿真计算 |
| LLaMA-Factory DPO 格式两连坑：role/content vs from/value；列名 prompt vs messages | sharegpt 格式 + `columns.messages`；报错「sequence item 0」即查此条 |
| modelscope CLI 无入口（venv 版本差异） | `python -m modelscope` 或 base 环境安装后用 `modelscope download` |

## 七、可复用资产

- `scripts/rtl_common.py` 双闸引擎（含 --selftest 离线自检）
- `scripts/parse_training_log.py` veRL 日志 → 指标 jsonl + 曲线图
- `scripts/slice_report.py` 全量报告按口径切片
- `ckpt_watchdog.sh` / `crash_watchdog.sh` 训练守护
- `scripts/e5_sample_teacher.py` / `annotate_samples.py` / `build_dpo_pairs.py`
  蒸馏-标注-构对三件套（E5/E6/E7 数据管线全部可复用）
