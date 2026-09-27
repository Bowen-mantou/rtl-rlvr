# -*- coding: utf-8 -*-
"""build_dpo_pairs.py — 从双闸标注结果直接构 DPO 偏好对（E7 数据，标注时同步收集）。

构对规则（同一 task_id 内，E5-E7 计划修订版）：
  chosen  = 仿真全过（k == N）的轨迹；多个取最先出现的
  rejected = 综合过但仿真错（synth_pass 且 k < N）的轨迹；多个取最先出现的
  两者都存在的题才构对；「综合失败」的轨迹不参与（信号最弱）
输出 LLaMA-Factory DPO 格式 jsonl：{"conversations": [...], "chosen": {...},
"rejected": {...}}——chosen/rejected 的 content 与训练格式对齐（<answer> 包裹）。

用法：
  python scripts/build_dpo_pairs.py --annotated data/e5/traj_teacher_full_annotated.jsonl \
      --out data/e7/dpo_pairs.jsonl
"""
import argparse
import json
import os
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotated", required=True, nargs="+",
                    help="annotate_samples.py 的产物（可多个来源合并）")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    by_task = defaultdict(list)
    for path in args.annotated:
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                by_task[r["task_id"]].append(r)

    pairs = []
    stats = {"paired": 0, "no_pos": 0, "no_neg": 0, "skipped_no_code": 0}
    for tid, rows in sorted(by_task.items()):
        chosen = next((r for r in rows if r["k"] == r["N"] and r["N"] > 0
                       and r["code"]), None)
        rejected = next((r for r in rows if r["synth_pass"]
                         and r["k"] < r["N"] and r["code"]), None)
        if chosen is None:
            stats["no_pos"] += 1
            continue
        if rejected is None:
            stats["no_neg"] += 1
            continue
        pairs.append({
            "task_id": tid,
            # LLaMA-Factory DPO 需要 sharegpt 风格（from/value）
            "conversations": [{"from": "human", "value": chosen["prompt"]}],
            "chosen": {"from": "gpt",
                       "value": f"<answer>\n{chosen['code']}\n</answer>"},
            "rejected": {"from": "gpt",
                         "value": f"<answer>\n{rejected['code']}\n</answer>"},
        })
        stats["paired"] += 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"[dpo-pairs] 构对 {stats['paired']} 对 → {args.out}")
    print(f"[dpo-pairs] 未构对：无正样本 {stats['no_pos']} 题 / "
          f"无负样本 {stats['no_neg']} 题")
    if stats["paired"] < 30:
        print("[dpo-pairs] ⚠ 对数偏少（<30），DPO 增益预期进一步下调，如实报告")


if __name__ == "__main__":
    main()
