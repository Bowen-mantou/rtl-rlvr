# -*- coding: utf-8 -*-
"""make_grpo_parquet.py — 统一 jsonl → veRL GRPO 训练 parquet。

输出列（veRL custom reward 标准形态，参考 Code-R1 E1 在跑的格式）：
  prompt         已套好 Qwen2.5 chat 模板的完整字符串（vLLM 原样 tokenize，
                 不依赖 veRL 版本差异的 apply_chat_template 配置）
  ground_truth   JSON 字符串 {"header": ..., "tests": [...], "gold": ...}，
                 reward_fn.py 用它跑双闸（gold 供无测试向量题目走参考 oracle）
  data_source    固定 "rtl-spec"（veRL 用该列路由奖励）
  reward_model   {"style": "rule"}（规则奖励标记）
  task_id        调试用（不影响训练）

val 集从 train 集尾部切 --val-n 题（确定性）。注意：GRPO 的 val 只用于训练期
监控，**不是**最终评估集 —— 最终评估用 eval split 的 10 题（口径纪律：最终
评估集不进训练也不进训练期 val）。

用法：
  python scripts/make_grpo_parquet.py --problems data/spec_set_50.jsonl \
      --split train --val-n 8 --out-dir data/grpo
  # 可选：并入 VerilogEval 清洗后的 train 题（扩大训练集）
  python scripts/make_grpo_parquet.py --problems data/spec_set_50.jsonl \
      data/verilogeval_cleaned.jsonl --split train --val-n 8 --out-dir data/grpo
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtl_common


def make_chat_prompt(problem):
    """构造 veRL 期望的 prompt 列：消息列表（不是预格式化字符串！）。

    2026-09-20 E3 首启实测：本版 veRL 的 RLHFDataset 会对 prompt 列调用
    tokenizer.apply_chat_template（官方 preprocessor 的约定就是 prompt=
    [{"role": "user", "content": ...}] 列表）。预格式化字符串会被 Jinja 模板
    当字符流迭代 → 只剩 ~24 token 的模板骨架 → 全部奖励 -0.1 的假训练。
    模板交给 veRL 套（与评估端同 tokenizer、同模板，口径一致）。
    """
    return [{"role": "user", "content": rtl_common.prompt_text(problem)}]


def build(problem_paths, split, val_n, out_dir, tokenizer_path=None):
    problems = []
    for path in problem_paths:
        loaded = rtl_common.load_problems(path)
        loaded = [p for p in loaded if p["split"] == split]
        print(f"[make_grpo] {path}: {split} split 取 {len(loaded)} 题")
        problems.extend(loaded)
    if not problems:
        raise SystemExit("没有题目（检查 --split 与输入文件）")
    problems.sort(key=lambda p: p["task_id"])

    val_ids = {p["task_id"] for p in problems[-val_n:]} if val_n else set()
    train_rows, val_rows = [], []
    for p in problems:
        gt = json.dumps({"header": p["header"], "tests": p["tests"],
                         "gold": p["module"]}, ensure_ascii=False)
        # 注意：veRL 0.10 的 naive reward manager 直接取
        #   non_tensor_batch["reward_model"]["ground_truth"]
        # reward_model 列必须是 dict（含 ground_truth 键），不能是 JSON 字符串
        #（2026-09-20 E3 首启崩溃实测教训）
        row = {"prompt": make_chat_prompt(p),
               "data_source": "rtl-spec",
               "reward_model": {"style": "rule", "ground_truth": gt},
               "task_id": p["task_id"]}
        (val_rows if p["task_id"] in val_ids else train_rows).append(row)
    if not train_rows:
        raise SystemExit(f"train 集为空（val_n={val_n} ≥ 题数？）")

    import pyarrow as pa
    import pyarrow.parquet as pq
    os.makedirs(out_dir, exist_ok=True)
    for name, rows in (("train", train_rows), ("val", val_rows)):
        t = pa.Table.from_pylist(rows)
        path = os.path.join(out_dir, f"{name}.parquet")
        pq.write_table(t, path)
        print(f"[make_grpo] {name}.parquet: {len(rows)} 行 → {path}")
    print("[make_grpo] 提示: prompt 已套 chat 模板，veRL 配置里不要再开 "
          "apply_chat_template")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", required=True, nargs="+", help="统一 jsonl（可多个）")
    ap.add_argument("--split", default="train", choices=["train", "eval", "all"])
    ap.add_argument("--val-n", type=int, default=8,
                    help="从尾部切多少题当训练期 val（0 = 不切）")
    ap.add_argument("--out-dir", default="data/grpo")
    ap.add_argument("--dry-run", action="store_true",
                    help="只校验不写盘（不要求 pyarrow 之外的东西）")
    args = ap.parse_args()
    if args.dry_run:
        problems = []
        for path in args.problems:
            problems.extend(p for p in rtl_common.load_problems(path)
                            if p["split"] == args.split)
        print(f"[dry-run] {len(problems)} 题待转 parquet（split={args.split}）")
        for p in problems[:2]:
            print("  样例 prompt 消息列表:", make_chat_prompt(p))
        return 0
    return build(args.problems, args.split, args.val_n, args.out_dir)


if __name__ == "__main__":
    main()
