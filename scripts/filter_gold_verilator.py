# -*- coding: utf-8 -*-
"""filter_gold_verilator.py — 剔除「参考实现过不了 Verilator 编译」的题目。

为什么需要：clean_data --annotate 只查了 Yosys（闸门①），但 oracle 模式的
仿真闸（闸门②）要求参考实现能被 Verilator 编译——gold 编译不过的题，
候选永远拿不到仿真分（黄金标准本身跑不起来），属于「不可判分题」。
评估/训练集里留着它们 = 分母虚高 + 训练时白浪费 reward 计算。
诚实纪律：剔除数量显式报告，不静默。

用法：
  python scripts/filter_gold_verilator.py --input data/verilogeval_cleaned.jsonl \
      --out data/verilogeval_cleaned.jsonl --workers 8
（--out 覆盖原文件前会打印剔除清单；train/eval split 原样保留）
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
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    problems = rtl_common.load_problems(args.input)
    missing = rtl_common.check_tools()
    if missing:
        raise SystemExit("缺少工具: " + ", ".join(missing))

    def check(p):
        dut = rtl_common.parse_header(p["header"])
        # 空测试列表 → harness 只编译不跑；编译成功 = gold 可被 Verilator 处理
        r = rtl_common.run_verilator_tests(p["module"], dut, [])
        return p, r["ok"], r["reason"], r["log_tail"]

    keep, dropped = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for p, ok, reason, tail in ex.map(check, problems):
            if ok:
                keep.append(p)
            else:
                dropped.append((p["task_id"], p["split"], reason))
                print(f"[drop] {p['task_id']} | {p['split']} | {reason}")

    n_eval_dropped = sum(1 for d in dropped if d[1] == "eval")
    print(f"[filter] 剔除 {len(dropped)} 题（eval {n_eval_dropped} / train "
          f"{len(dropped) - n_eval_dropped}），保留 {len(keep)} 题")
    with open(args.out, "w", encoding="utf-8") as f:
        for p in keep:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"[filter] 已写 → {args.out}")
    print("注意: 若 --out 覆盖了原文件，completions 里被剔除题的采样行也要删掉"
          "（eval 会对未知 task_id 报错）")


if __name__ == "__main__":
    main()
