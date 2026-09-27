# -*- coding: utf-8 -*-
"""annotate_samples.py — completions 双闸标注 → verifier 训练数据（E4 可选）。

输入：题库 jsonl + 模型 completions jsonl（eval_rtl.py generate 的产物，
多个模型的 completions 可以合并后一次标注）。
输出：verifier jsonl，每行：
  {"prompt": <spec+header 文本>, "code": <解析出的完整 module>,
   "k": <通过测试数（综合失败 = 0）>, "N": <测试总数>, "synth_pass": bool,
   "source": <模型名>}

k/N 语义与 Code-R1 verifier 数据一致（沙箱标 k/N 的 RTL 版）。
末尾打印分布统计；若 k 全为 0 或全为 N（无信号），明确告警 —— 这样的数据
训不出有用的 verifier（静默降级教训）。

用法：
  python scripts/annotate_samples.py --problems data/spec_set_50.jsonl \
      --completions results/e1/completions.jsonl \
      --out data/verifier/e1_annotated.jsonl
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtl_common


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", required=True)
    ap.add_argument("--completions", required=True, nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    missing = rtl_common.check_tools()
    if missing:
        raise SystemExit("缺少工具: " + ", ".join(missing) +
                         "\n安装: sudo apt install -y yosys verilator build-essential"
                         "\n（没有工具时禁止标注——否则会把所有样本静默标成 0 分）")
    problems = {p["task_id"]: p for p in rtl_common.load_problems(args.problems)}
    comps = []
    for path in args.completions:
        if not os.path.exists(path):
            raise SystemExit(f"completions 不存在: {path}")
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    comps.append(json.loads(line))
    print(f"[annotate] {len(comps)} 条 completion 待标注")

    def work(c):
        p = problems[c["task_id"]]
        code = rtl_common.extract_module_lenient(c["completion"])
        if code is None:
            return {"task_id": c["task_id"], "prompt": rtl_common.prompt_text(p), "code": "",
                    "k": 0, "N": len(p["tests"]), "synth_pass": False,
                    "source": c.get("model", "?")}
        r = rtl_common.evaluate_module(code, p)
        return {"task_id": c["task_id"], "prompt": rtl_common.prompt_text(p), "code": code,
                "k": r["n_pass"], "N": r["n_total"],
                "synth_pass": r["synth_ok"], "source": c.get("model", "?")}

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(work, comps):
            rows.append(r)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dist = {}
    for r in rows:
        dist[(r["k"], r["N"])] = dist.get((r["k"], r["N"]), 0) + 1
    print(f"[annotate] 已写 {len(rows)} 条 → {args.out}")
    print(f"[annotate] k/N 分布: {dist}")
    ks = {r["k"] for r in rows}
    if len(ks) <= 1:
        print(f"[annotate] ⚠ 所有样本 k 都相同（{ks}）—— verifier 数据无信号，"
              f"训练前先扩充来源/检查判分链路（静默降级教训）")
    return 0


if __name__ == "__main__":
    main()
