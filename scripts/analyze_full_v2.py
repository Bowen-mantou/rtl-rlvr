# -*- coding: utf-8 -*-
"""analyze_full_v2.py — 全量 V2 评估结果分析：官方口径 + seen/unseen 分层 + FSM 修复推演。

用法（实例上）：
  python scripts/analyze_full_v2.py --report results/full_v2_e3/report.json \
      --problems data/verilogeval_cleaned.jsonl
输出：
  1. 全集 pass@1（官方口径，含 62 题模型见过的训练题）
  2. unseen 36 题 pass@1（干净泛化口径，即老评估集里 V2 部分的同口径数字）
  3. 分档表（comb/seq/fsm）
  4. what-if 推演：fsm 提到 comb 水平 → 全集总分
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--problems", required=True)
    args = ap.parse_args()

    report = json.load(open(args.report, encoding="utf-8"))
    problems = {}
    for line in open(args.problems, encoding="utf-8"):
        p = json.loads(line)
        problems[p["task_id"]] = p

    rows = report["rows"]
    by_tier, by_split = {}, {}
    for r in rows:
        p = problems[r["task_id"]]
        tier, split = p["tier"], p["split"]
        for d, key in ((by_tier, tier), (by_split, split)):
            d.setdefault(key, [0, 0])
            d[key][1] += 1
            d[key][0] += r["overall"]

    total = sum(v[0] for v in by_tier.values())
    n = sum(v[1] for v in by_tier.values())
    print(f"=== 全集官方口径：pass@1 = {total}/{n} = {total / n:.4f} ===")
    for split, (ok, cnt) in sorted(by_split.items()):
        tag = "seen（训练见题）" if split == "train" else "unseen（干净泛化）"
        print(f"  {split:5s} ({tag}): {ok}/{cnt} = {ok / cnt:.4f}")
    print("分档：")
    comb_rate = None
    for tier, (ok, cnt) in sorted(by_tier.items()):
        print(f"  {tier:14s}: {ok}/{cnt} = {ok / cnt:.4f}")
        if tier == "combinational":
            comb_rate = ok / cnt
    if comb_rate is not None:
        fsm_ok, fsm_n = by_tier.get("fsm", (0, 0))
        new_total = total - fsm_ok + round(comb_rate * fsm_n)
        print(f"what-if：fsm 提到 comb 水平（{comb_rate:.4f}）→ "
              f"全集 {new_total}/{n} = {new_total / n:.4f}")


if __name__ == "__main__":
    main()
