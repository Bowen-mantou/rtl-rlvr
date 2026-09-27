# -*- coding: utf-8 -*-
"""reward_fn.py — RTL 双闸奖励（veRL custom reward function）。

严格按 docs/项目设计.md 第三节实现，不做自由发挥：

  格式    ：<answer> 内解析出完整 module → +0.1；解析失败 → -0.1（无正确性分）
  正确性  ：Yosys 综合失败 → 0
            综合通过 + Verilator 仿真全测试通过 → 1.0
            综合通过 + 部分测试通过 → 0（保持二进制，与方法论平移叙事一致）
  总分 ∈ {-0.1, 0.1, 1.1}（满分 1.1，与 Code-R1 同构）

可选开关（全部默认关，通过 reward_kwargs 打开；E 系列单独验证——加分设计）：
  split_reward=True   综合与仿真拆两段：综合 +0.3 过程信号、仿真 +0.7 结果信号
                      （总分 ∈ {-0.1, 0.1, 0.4, 1.1}；客观执行产生，无手写 PRM 风险）
  lint_bonus=True     行为级过程奖励（设计文档加分设计二）：verilator --lint-only
                      -Wall 警告映射 BLKSEQ/BLKANDNBLK/WIDTH/UNDRIVEN/COMBDLY/
                      CASEOVERLAP 各 -0.03~-0.05，零警告 +0.1，封顶 ±0.2
  use_verifier=True   E4 可选：Result + λ·V（extra_info 注入 verifier_score，
                      模式同 Code-R1 E7，λ 默认 0.1）

实现说明：
  - 闸门用 subprocess 调 yosys/verilator（不依赖 flashinfer；超时杀进程组）
  - 判分逻辑与评估完全同源（scripts/rtl_common.py 同一份实现，口径纪律）
  - 结果按 (code, tests) 哈希缓存：工具执行是确定性的，缓存只提速不改数
  - 并发：ThreadPoolExecutor(num_processes)，默认 8
  - 异常轨迹（解析失败/综合失败）默认仍给分（-0.1/0.1），让 GRPO 组内优势
    自然压低它们；如需「剔除后组内重算优势」，设环境变量 RTL_REWARD_ABNORMAL=1
    返回 {"score": float, "abnormal": bool}（需 veRL 版本支持 dict 返回，
    默认关闭 —— 与 run_e1.sh 的 float 返回路径保持一致）

veRL 接线（run_grpo.sh 已配好）：
  reward.custom_reward_function.path=<本文件绝对路径>
  reward.custom_reward_function.name=compute_score
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "scripts"))
import rtl_common

FORMAT_BONUS = 0.1
FORMAT_PENALTY = -0.1
CORRECT_BONUS = 1.0
SPLIT_SYNTH_BONUS = 0.3
SPLIT_SIM_BONUS = 0.7

# lint 规则映射（设计文档第三节加分设计二；规则由 verilator 定义，非手写拍脑袋）
LINT_RULES = {
    "BLKSEQ": -0.05, "BLKANDNBLK": -0.05, "WIDTH": -0.03,
    "UNDRIVEN": -0.05, "COMBDLY": -0.05, "CASEOVERLAP": -0.05,
}
LINT_ZERO_WARN_BONUS = 0.1
LINT_CAP = 0.2

_LINT_CACHE = {}


def _lint_score(code, timeout=60):
    """verilator --lint-only -Wall 警告 → 行为奖励（封顶 ±LINT_CAP）。"""
    key = code
    if key in _LINT_CACHE:
        return _LINT_CACHE[key]
    if not rtl_common._which("verilator"):
        return 0.0
    workdir = tempfile.mkdtemp(prefix="rtl_lint_")
    try:
        src = os.path.join(workdir, "candidate.v")
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
        proc = subprocess.run(
            ["verilator", "--lint-only", "-Wall", "candidate.v"],
            capture_output=True, text=True, timeout=timeout, cwd=workdir)
        out = (proc.stdout or "") + (proc.stderr or "")
        if "Error" in out or "error" in out:
            return 0.0  # lint 都不过的代码不额外加分
        score = 0.0
        for rule, delta in LINT_RULES.items():
            if re.search(rf"%Warning-{rule}", out):
                score += delta
        if not re.search(r"%Warning", out):
            score += LINT_ZERO_WARN_BONUS
        score = max(-LINT_CAP, min(LINT_CAP, score))
        _LINT_CACHE[key] = score
        return score
    except subprocess.TimeoutExpired:
        return 0.0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _score_one(data_source, solution_str, ground_truth, split_reward=False,
               lint_bonus=False, use_verifier=False, lambda_v=0.1, extra_info=None):
    """单样本打分。总分 ∈ {-0.1, 0.1, 1.1}（split 模式 ∈ {-0.1, 0.1, 0.4, 1.1}）。"""
    if isinstance(ground_truth, dict):
        gt = ground_truth.get("ground_truth", ground_truth)
    else:
        gt = ground_truth
    try:
        if isinstance(gt, str):
            gt = json.loads(gt)
    except json.JSONDecodeError:
        gt = {}

    code = rtl_common.extract_module_strict(solution_str or "")
    if code is None:
        # 格式坏：负分（防钻空子）；无正确性分
        score = FORMAT_PENALTY
        abnormal = True
        if use_verifier:
            return score, abnormal  # 没有 module 就没有 verifier 输入
        return score, abnormal

    header = gt.get("header", "")
    if not header:
        score, abnormal = FORMAT_PENALTY, True
        return score, abnormal

    problem = {"header": header, "tests": gt.get("tests") or [],
               "module": gt.get("gold") or ""}
    r = rtl_common.evaluate_module(code, problem)
    if r["overall"]:
        score = FORMAT_BONUS + CORRECT_BONUS
    elif r["synth_ok"]:
        # 综合过 + 部分测试过 → 正确性 0（设计文档：保持二进制）
        score = FORMAT_BONUS + (SPLIT_SYNTH_BONUS if split_reward else 0.0)
    else:
        score = FORMAT_BONUS
    abnormal = not r["synth_ok"]

    if lint_bonus:
        score += _lint_score(code)

    if use_verifier and r["synth_ok"]:
        v = None
        if isinstance(extra_info, dict):
            v = extra_info.get("verifier_score")
            if v is None and isinstance(extra_info.get("extra_fields"), dict):
                v = extra_info["extra_fields"].get("verifier_score")
        v = float(v or 0.0)
        result_bin = 1.0 if r["overall"] else 0.0
        score = result_bin + lambda_v * v

    if os.environ.get("DEBUG_REWARD_FN"):
        print(f"[reward_fn] ds={data_source} synth={r['synth_ok']} "
              f"sim={r['sim_ok']} score={score:.3f} reason={r['reason'][:60]}",
              flush=True)
    return score, abnormal


def compute_score(data_source, solution_str, ground_truth, extra_info=None,
                  split_reward=False, lint_bonus=False, use_verifier=False,
                  lambda_v=0.1, num_processes=8, **kwargs):
    """veRL 奖励入口（naive manager 逐样本调 / batch manager 传列表）。

    默认返回 float（与 run_e1.sh 实测路径一致）；设 RTL_REWARD_ABNORMAL=1 时
    返回 {"score": float, "abnormal": bool}（供「剔除异常轨迹重算优势」，
    需当前 veRL 版本支持 dict 返回 —— 默认关闭）。
    """
    if isinstance(solution_str, list):
        n = len(solution_str)
        dss = data_source if isinstance(data_source, list) else [data_source] * n
        gts = ground_truth if isinstance(ground_truth, list) else [ground_truth] * n
        eis = extra_info if isinstance(extra_info, list) else [extra_info] * n
        if n > 1 and num_processes > 1:
            # verilator 编译是重活：batch 调用时内部并行（缓存线程安全）
            from concurrent.futures import ThreadPoolExecutor
            def work(i):
                return _score_one(dss[i], solution_str[i], gts[i],
                                  split_reward=split_reward, lint_bonus=lint_bonus,
                                  use_verifier=use_verifier, lambda_v=lambda_v,
                                  extra_info=eis[i])
            with ThreadPoolExecutor(max_workers=num_processes) as ex:
                results = list(ex.map(work, range(n)))
            scores = [s for s, _ in results]
            abnormals = [a for _, a in results]
        else:
            scores, abnormals = [], []
            for i in range(n):
                s, a = _score_one(dss[i], solution_str[i], gts[i],
                                  split_reward=split_reward, lint_bonus=lint_bonus,
                                  use_verifier=use_verifier, lambda_v=lambda_v,
                                  extra_info=eis[i])
                scores.append(s)
                abnormals.append(a)
    else:
        scores, abnormals = [], []
        s, a = _score_one(data_source, solution_str, ground_truth,
                          split_reward=split_reward, lint_bonus=lint_bonus,
                          use_verifier=use_verifier, lambda_v=lambda_v,
                          extra_info=extra_info)
        scores.append(s)
        abnormals.append(a)

    if os.environ.get("RTL_REWARD_ABNORMAL") == "1":
        out = [{"score": float(s), "abnormal": bool(a)}
               for s, a in zip(scores, abnormals)]
        return out[0] if len(out) == 1 else out
    return float(scores[0]) if len(scores) == 1 else [float(s) for s in scores]
