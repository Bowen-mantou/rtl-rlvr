# -*- coding: utf-8 -*-
"""eval_rtl.py — 双闸评估脚本（Yosys 综合 + Verilator 仿真），E1-E4 全模型共用。

口径纪律（docs/项目设计.md 第八节）：
  - 所有模型同一脚本、同一次采样（默认贪心解码 n=1 → pass@1 = 通过率均值）
  - 分层指标：总通过率（双闸全过）/ 综合通过率 / 仿真通过率（另报「综合过者中仿真过」）
  - 格式达标率（输出含 <answer> 且其中解析出完整 module）单独统计，不进主指标
  - 不做任何美化数字的事：每题的失败原因（synth 日志尾部 / 第一个失败步骤）全部保留

模式：
  refcheck   验证数据集参考实现全部通过自己的双闸（开训前必跑，等同 build_spec_set --verify）
  generate   模型 + 题库 → 采样出 completions jsonl（生成与判分解耦，判分可在无卡模式跑）
  eval       题库 + completions jsonl → 报告（json + markdown 双格式）
  pipe       generate + eval 一步到位
  dry-run    静态检查（配置键/路径/文件就位/测试向量合法性），不调工具不加载模型

用法示例：
  # E1 基线（零样本基座模型，pass@1）：
  python scripts/eval_rtl.py pipe --problems data/spec_set_50.jsonl \
      --model /root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct \
      --split eval --out-dir results/e1

  # 只判分（completions 已生成；判分纯 CPU，无卡模式 ¥0.1/h 可跑）：
  python scripts/eval_rtl.py eval --problems data/spec_set_50.jsonl \
      --completions results/e1/completions.jsonl --out results/e1/e1_report

  # 数据自检：
  python scripts/eval_rtl.py refcheck --problems data/spec_set_50.jsonl

completions jsonl 格式（generate 输出 / eval 输入）：
  {"task_id": "spec50-comb-001", "completion": "<answer>module ... endmodule</answer>",
   "model": "Qwen2.5-Coder-3B-Instruct", "sample_idx": 0}
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtl_common


# ---------------------------------------------------------------------------
# 生成（模型 → completions）
# ---------------------------------------------------------------------------

def make_stopping_criteria(tokenizer):
    """基于 transformers StoppingCriteria 的 </answer> 停词。"""
    from transformers import StoppingCriteria, StoppingCriteriaList
    ids = tokenizer.encode("</answer>", add_special_tokens=False)
    if not ids:
        return None

    class AnswerStop(StoppingCriteria):
        def __call__(self, input_ids, scores, **kwargs):
            seq = input_ids[0].tolist()
            return len(seq) >= len(ids) and seq[-len(ids):] == ids

    return StoppingCriteriaList([AnswerStop()])


def generate_completions(problems, model_path, out_path, n=1, max_new_tokens=1024,
                         do_sample=False, temperature=0.8, seed=42):
    """模型采样。默认贪心（do_sample=False，确定性，pass@1 主口径）。

    逐题生成（不做 batch）：本题规模 10-60 题 × 3B 模型，单题 2-5 秒，
    batch 省不了几分钟，但会给 </answer> 停词和 padding 引入版本兼容风险
    （PITFALLS：LCB 批生成提速方案实测没赢 —— 简单优先）。
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[generate] 加载模型 {model_path} ...")
    tok = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    # PITFALLS：transformers 5.x 禁止传 attn_implementation；dtype 必须用 torch 对象
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, trust_remote_code=True)
    model.eval()
    if torch.cuda.is_available():
        model = model.cuda()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[generate] device={device}, 题目 {len(problems)} × n={n}, "
          f"贪心={not do_sample}")

    model_name = os.path.basename(model_path.rstrip("/"))
    stop = make_stopping_criteria(tok)
    gen_kwargs = dict(max_new_tokens=max_new_tokens, do_sample=do_sample,
                      pad_token_id=tok.pad_token_id or tok.eos_token_id,
                      eos_token_id=tok.eos_token_id)
    if do_sample:
        gen_kwargs.update(temperature=temperature, top_p=0.95)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    rows = []
    with open(out_path, "w", encoding="utf-8") as f:
        for p in problems:
            text = rtl_common.prompt_text(p)
            try:
                prompt = tok.apply_chat_template(
                    [{"role": "user", "content": text}],
                    add_generation_prompt=True, tokenize=False)
            except Exception:
                prompt = rtl_common.apply_qwen_chat(text)
            for sample_idx in range(n):
                enc = tok(prompt, return_tensors="pt").to(device)
                with torch.no_grad():
                    try:
                        out = model.generate(**enc, stopping_criteria=stop,
                                             **gen_kwargs)
                    except TypeError:
                        # transformers 新版弃用 stopping_criteria → stop_strings
                        out = model.generate(**enc, stop_strings=["</answer>"],
                                             **gen_kwargs)
                resp = tok.decode(out[0][enc["input_ids"].shape[1]:],
                                  skip_special_tokens=True)
                row = {"task_id": p["task_id"], "completion": resp,
                       "model": model_name, "sample_idx": sample_idx}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                rows.append(row)
            print(f"  [gen] {p['task_id']} 完成 {n}/{n}", flush=True)
    print(f"[generate] 已写 {len(rows)} 条 → {out_path}")
    return rows


# ---------------------------------------------------------------------------
# 判分
# ---------------------------------------------------------------------------

def load_completions(path):
    """读 completions jsonl；坏行报错退出（口径纪律：不静默跳过）。"""
    rows = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{ln} JSON 解析失败: {e}")
            if "task_id" not in r or "completion" not in r:
                raise SystemExit(f"{path}:{ln} 缺 task_id/completion 字段: {r}")
            rows.append(r)
    return rows


def evaluate(problems, completions, out_path, workers=8, use_oracle=True, seed=42):
    """双闸判分 + 报告。"""
    from concurrent.futures import ThreadPoolExecutor

    by_id = {}
    for p in problems:
        by_id[p["task_id"]] = p
    per_problem = {tid: [] for tid in by_id}
    for c in completions:
        if c["task_id"] not in by_id:
            raise SystemExit(f"completion 引用了题库中不存在的 task_id: "
                             f"{c['task_id']}（口径纪律：多出的行必须查明，不许跳过）")
        per_problem[c["task_id"]].append(c)
    missing = [tid for tid, v in per_problem.items() if not v]
    if missing:
        raise SystemExit(f"题库中有 {len(missing)} 题没有 completion（采样缺失，"
                         f"必须补跑，不能当 0 分跳过）: {missing[:5]}...")

    tasks = []
    for tid, cs in per_problem.items():
        for c in cs:
            code = rtl_common.extract_module_lenient(c["completion"])
            tasks.append((tid, c, code))
    print(f"[eval] 开始双闸判分：{len(tasks)} 条 completion × {workers} workers")

    def work(item):
        tid, c, code = item
        p = by_id[tid]
        row = {"task_id": tid, "sample_idx": c.get("sample_idx", 0),
               "model": c.get("model", "?"),
               "format_ok": rtl_common.extract_module_strict(c["completion"]) is not None}
        if code is None:
            row.update({"synth_ok": False, "sim_ok": False, "overall": False,
                        "n_pass": 0, "n_total": len(p["tests"]),
                        "reason": "no_module_extracted", "synth_log": "",
                        "sim_log": ""})
        else:
            r = rtl_common.evaluate_module(code, p, use_oracle=use_oracle, seed=seed)
            row.update({k: r[k] for k in ("synth_ok", "sim_ok", "overall",
                                          "n_pass", "n_total", "reason",
                                          "synth_log", "sim_log")})
        return row

    rows = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(work, tasks):
            rows.append(r)

    # ---- 聚合（n 样本 pass@1 无偏估计：c/n）----
    agg = {"n_problems": len(problems), "n_completions": len(rows)}
    for key in ("overall", "synth_ok", "sim_ok", "format_ok"):
        agg[f"rate_{key}"] = sum(1 for r in rows if r[key]) / len(rows)
    synth_ok_rows = [r for r in rows if r["synth_ok"]]
    agg["rate_sim_given_synth"] = (
        sum(1 for r in synth_ok_rows if r["sim_ok"]) / len(synth_ok_rows)
        if synth_ok_rows else float("nan"))
    agg["pass1"] = sum(1 for r in rows if r["overall"]) / len(rows)

    tiers = {}
    for p in problems:
        tiers.setdefault(p["tier"], []).append(p["task_id"])
    agg["by_tier"] = {}
    for tier, tids in tiers.items():
        sub = [r for r in rows if r["task_id"] in tids]
        agg["by_tier"][tier] = {
            "n": len(sub),
            "pass1": sum(1 for r in sub if r["overall"]) / len(sub) if sub else 0.0,
            "synth_rate": sum(1 for r in sub if r["synth_ok"]) / len(sub) if sub else 0.0,
            "sim_rate": sum(1 for r in sub if r["sim_ok"]) / len(sub) if sub else 0.0,
        }

    # ---- 失败原因统计（诚实：全部保留）----
    fail_reasons = {}
    for r in rows:
        if not r["overall"]:
            key = r["reason"].split(":")[0] if r["reason"] else "unknown"
            fail_reasons[key] = fail_reasons.get(key, 0) + 1
    agg["fail_reasons"] = fail_reasons

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path + ".json", "w", encoding="utf-8") as f:
        json.dump({"aggregates": agg, "rows": rows}, f, ensure_ascii=False, indent=2)
    with open(out_path + ".md", "w", encoding="utf-8") as f:
        f.write(f"# RTL 双闸评估报告\n\n"
                f"- 题目数: {agg['n_problems']} | completion 数: {agg['n_completions']}\n\n"
                f"| 指标 | 值 |\n|---|---|\n"
                f"| **pass@1（双闸全过）** | **{agg['pass1']:.4f}** |\n"
                f"| 综合通过率 | {agg['rate_synth_ok']:.4f} |\n"
                f"| 仿真通过率 | {agg['rate_sim_ok']:.4f} |\n"
                f"| 仿真通过率（综合过者中） | {agg['rate_sim_given_synth']:.4f} |\n"
                f"| 格式达标率（<answer> 内解析出 module） | {agg['rate_format_ok']:.4f} |\n\n"
                f"## 分档\n\n| 档位 | 题数 | pass@1 | 综合率 | 仿真率 |\n|---|---|---|---|---|\n")
        for tier, t in agg["by_tier"].items():
            f.write(f"| {tier} | {t['n']} | {t['pass1']:.4f} | "
                    f"{t['synth_rate']:.4f} | {t['sim_rate']:.4f} |\n")
        if fail_reasons:
            f.write(f"\n## 失败原因分布\n\n| 原因 | 次数 |\n|---|---|\n")
            for k, v in sorted(fail_reasons.items(), key=lambda x: -x[1]):
                f.write(f"| {k} | {v} |\n")
        f.write("\n## 逐题明细\n\n| task_id | tier | 综合 | 仿真 | 双闸 | 失败原因 |\n"
                "|---|---|---|---|---|---|\n")
        for r in sorted(rows, key=lambda x: (x["task_id"], x["sample_idx"])):
            f.write(f"| {r['task_id']} | {by_id[r['task_id']]['tier']} | "
                    f"{'✓' if r['synth_ok'] else '✗'} | "
                    f"{'✓' if r['sim_ok'] else '✗'} | "
                    f"{'✓' if r['overall'] else '✗'} | "
                    f"{(r['reason'] or '')[:80]} |\n")

    print(f"[eval] pass@1 = {agg['pass1']:.4f} "
          f"(综合 {agg['rate_synth_ok']:.4f} / 仿真 {agg['rate_sim_ok']:.4f} / "
          f"格式 {agg['rate_format_ok']:.4f})")
    print(f"[eval] 报告 → {out_path}.json / {out_path}.md")
    return agg


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------

def cmd_refcheck(args):
    from build_spec_set import verify
    return verify(args.problems[0], args.workers)


def cmd_generate(args):
    problems, seen = [], set()
    for path in args.problems:
        for p in rtl_common.load_problems(path):
            if p["task_id"] in seen:
                continue
            seen.add(p["task_id"])
            if args.split == "all" or p["split"] == args.split:
                problems.append(p)
    out = os.path.join(args.out_dir, "completions.jsonl")
    generate_completions(problems, args.model, out, n=args.n,
                         max_new_tokens=args.max_new_tokens, do_sample=args.sample)
    print(f"下一步判分: python scripts/eval_rtl.py eval --problems "
          f"{' '.join(args.problems)} --completions {out} --out "
          f"{os.path.join(args.out_dir, 'report')} --split {args.split}")
    return 0


def cmd_eval(args):
    problems, seen = [], set()
    for path in args.problems:
        for p in rtl_common.load_problems(path):
            if p["task_id"] in seen:
                continue
            seen.add(p["task_id"])
            problems.append(p)
    if args.split != "all":
        problems = [p for p in problems if p["split"] == args.split]
    comps = load_completions(args.completions)
    comps = [c for c in comps
             if args.split == "all" or c["task_id"] in {p["task_id"] for p in problems}]
    evaluate(problems, comps, args.out, workers=args.workers,
             use_oracle=not args.no_oracle)
    return 0


def cmd_pipe(args):
    rc = cmd_generate(args)
    if rc:
        return rc
    args.completions = os.path.join(args.out_dir, "completions.jsonl")
    args.out = os.path.join(args.out_dir, "report")
    return cmd_eval(args)


def cmd_dry_run(args):
    problems = rtl_common.load_problems(args.problems[0])
    if args.split != "all":
        problems = [p for p in problems if p["split"] == args.split]
    print(f"[dry-run] 题库 {len(problems)} 题校验通过")
    missing = rtl_common.check_tools()
    if missing:
        print(f"[dry-run] ⚠ 缺少工具: {missing} —— 判分前需 "
              f"`sudo apt install -y yosys verilator build-essential`")
    else:
        print("[dry-run] yosys/verilator/make/g++ 就位")
    if args.completions:
        comps = load_completions(args.completions)
        ids = {p["task_id"] for p in problems}
        n_ok = sum(1 for c in comps if c["task_id"] in ids)
        n_extract = sum(1 for c in comps
                        if rtl_common.extract_module_lenient(c["completion"]))
        print(f"[dry-run] completions {len(comps)} 条，题目匹配 {n_ok}，"
              f"可解析出 module {n_extract} 条")
        if n_ok != len(comps):
            return 1
    if args.model:
        print(f"[dry-run] 生成模型路径: {args.model}（未加载，只验证存在）")
        if not os.path.isdir(args.model):
            print(f"[dry-run] ❌ 模型目录不存在: {args.model}")
            return 1
    print("[dry-run] OK —— 配置/路径/文件全部就位")
    return 0


def main():
    ap = argparse.ArgumentParser(description="RTL 双闸评估（Yosys + Verilator）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ("refcheck", "generate", "eval", "pipe", "dry-run"):
        sp = sub.add_parser(name, help={"refcheck": "验证参考实现过双闸",
                                        "generate": "模型采样 → completions",
                                        "eval": "completions 双闸判分",
                                        "pipe": "生成+判分一步到位",
                                        "dry-run": "静态检查不跑工具"}[name])
        sp.add_argument("--problems", required=True, nargs="+",
                        help="题库 jsonl（一个或多个）")
        sp.add_argument("--workers", type=int, default=8)
        if name in ("generate", "pipe", "dry-run"):
            sp.add_argument("--model", default=None, help="模型目录（HF 格式）")
        if name in ("generate", "pipe"):
            sp.add_argument("--out-dir", required=True)
            sp.add_argument("--n", type=int, default=1, help="每题采样数（pass@1）")
            sp.add_argument("--max-new-tokens", type=int, default=1024)
            sp.add_argument("--sample", action="store_true",
                            help="启用采样解码（默认贪心）")
        if name in ("eval", "pipe", "dry-run"):
            sp.add_argument("--completions", default=None,
                            help="completions jsonl（eval/pipe 必填）")
            sp.add_argument("--no-oracle", action="store_true",
                            help="禁用无测试向量题目的参考 oracle 判分")
        if name == "eval":
            sp.add_argument("--out", required=True, help="报告输出前缀（.json/.md）")
        if name == "pipe":
            sp.add_argument("--out", default=None,
                            help=argparse.SUPPRESS)  # pipe 内部从 --out-dir 推导
        sp.add_argument("--split", default="all", choices=["all", "train", "eval"],
                        help="只评估指定 split（默认全部）")
    args = ap.parse_args()

    # 参数校验（dry-run 的职责：配置键、路径、文件就位）
    for p in args.problems:
        if not os.path.exists(p):
            raise SystemExit(f"题库不存在: {p}（先用 build_spec_set.py 生成，"
                             f"或检查相对路径——脚本从项目根目录运行）")
    if getattr(args, "completions", None) and not os.path.exists(args.completions):
        raise SystemExit(f"completions 不存在: {args.completions}")

    rc = {"refcheck": cmd_refcheck, "generate": cmd_generate, "eval": cmd_eval,
          "pipe": cmd_pipe, "dry-run": cmd_dry_run}[args.cmd](args)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
