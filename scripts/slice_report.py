# -*- coding: utf-8 -*-
"""slice_report.py — 全量评估报告按子集切片，与历史实验同口径对比。

用法（实例上）：
  python scripts/slice_report.py --report results/p0a_eval_all/report.json
"""
import argparse
import json

EVAL_SPEC = {"spec50-comb-001", "spec50-comb-010", "spec50-comb-014",
             "spec50-comb-019", "spec50-seq-001", "spec50-seq-004",
             "spec50-seq-011", "spec50-seq-013", "spec50-fsm-001",
             "spec50-fsm-003", "spec50-fsm-011", "spec50-fsm-012",
             "spec50-fsm-013", "spec50-fsm-014"}


def rate(rows):
    return sum(r["overall"] for r in rows) / len(rows) if rows else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    rows = json.load(open(args.report, encoding="utf-8"))["rows"]

    v2 = [r for r in rows if r["task_id"].startswith("verilogeval")]
    v2_easy = [r for r in v2 if int(r["task_id"].split("Prob")[1]) <= 47]
    v2_hard = [r for r in v2 if int(r["task_id"].split("Prob")[1]) > 47]
    spec_eval = [r for r in rows if r["task_id"] in EVAL_SPEC]
    fsm = [r for r in rows if "-fsm-" in r["task_id"]]

    print(f"总题数: {len(rows)}")
    print(f"V2 全集 98 题:      {rate(v2):.4f}（E3 对比: 0.3367）")
    print(f"  V2 简单(≤47):     {rate(v2_easy):.4f}（E3 对比: 0.6667）")
    print(f"  V2 难题(>47):     {rate(v2_hard):.4f}（E3 对比: 0.1452）")
    print(f"扩展集 50 题:       {rate(spec_eval + v2_easy):.4f}（E3 对比: 0.6000）")
    print(f"FSM 6 题:           {rate(fsm):.4f}（E3 对比: 0.3333）")


if __name__ == "__main__":
    main()
