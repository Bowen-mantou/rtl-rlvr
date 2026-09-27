# -*- coding: utf-8 -*-
"""filter_sft_positives.py — 双闸标注结果 → E5 SFT 正样本数据集（alpaca 格式）。

过滤规则（E5 计划步骤 3）：
  保留：仿真全过（k == N > 0）的轨迹 → 正样本
  丢弃：综合过仿真错（留给 build_dpo_pairs.py 当 E7 负样本）、综合失败、
        无 module 的轨迹
去重：
  1. 同 code 的 md5 去重（采样重复）
  2. --dedup-against 给定时，与已有 SFT 数据的 output md5 去重（E2 教过的
     不重复喂——E5 的价值在「补 E2 没见过的分布」）
输出：LLaMA-Factory alpaca jsonl（instruction=prompt_text，output=<answer>包裹）

用法：
  python scripts/filter_sft_positives.py --annotated data/e5/traj_teacher_full_annotated.jsonl \
      --out data/sft/sft_alpaca_e5.jsonl \
      --dedup-against data/sft/sft_alpaca.json
"""
import argparse
import hashlib
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotated", required=True, nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dedup-against", default=[], nargs="+",
                    help="已有 SFT alpaca 数据（按 output md5 去重）")
    args = ap.parse_args()

    seen_codes = set()
    # 已有数据的 output md5 集合
    for path in args.dedup_against:
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                seen_codes.add(hashlib.md5(r["output"].encode()).hexdigest())

    kept, dropped = 0, {"sim_fail": 0, "synth_fail": 0, "dup": 0}
    rows = []
    for path in args.annotated:
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if not (r["k"] == r["N"] and r["N"] > 0 and r["code"]):
                    if r["synth_pass"]:
                        dropped["sim_fail"] += 1
                    else:
                        dropped["synth_fail"] += 1
                    continue
                out_text = f"<answer>\n{r['code']}\n</answer>"
                key = hashlib.md5(out_text.encode()).hexdigest()
                if key in seen_codes:
                    dropped["dup"] += 1
                    continue
                seen_codes.add(key)
                rows.append({"instruction": r["prompt"], "input": "",
                             "output": out_text})
                kept += 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[filter] 正样本 {kept} 条 → {args.out}")
    print(f"[filter] 丢弃：仿真不过 {dropped['sim_fail']}（进 E7 构对池）/ "
          f"综合失败 {dropped['synth_fail']} / 去重 {dropped['dup']}")
    if kept < 100:
        print("[filter] ⚠ 正样本 < 100 条，E5 SFT 增益预期下调，如实报告")


if __name__ == "__main__":
    main()
