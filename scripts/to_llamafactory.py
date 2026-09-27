# -*- coding: utf-8 -*-
"""to_llamafactory.py — 统一 jsonl → LLaMA-Factory alpaca 格式 SFT 数据集。

输出：{"instruction": <spec + 接口契约 + 格式要求>, "input": "", "output": <answer 包裹的参考实现>}
LLaMA-Factory 的 qwen 模板会自行套 chat 格式，instruction 放纯文本即可。

SFT 目标（设计文档第三节阶段 1）：学 Verilog 语法 + module 格式习惯 —— 所以
output 教的是完整响应形态 `<answer>module ... endmodule</answer>`，E2 评估时
格式达标率应显著高于 E1（这是「SFT 学格式」的量化证据）。

用法：
  python scripts/to_llamafactory.py --problems data/spec_set_50.jsonl \
      --split train --out data/sft/sft_alpaca.json
  # 可选并入 VerilogEval train 题
  python scripts/to_llamafactory.py --problems data/spec_set_50.jsonl \
      data/verilogeval_cleaned.jsonl --split train --out data/sft/sft_alpaca.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtl_common


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", required=True, nargs="+", help="统一 jsonl（可多个）")
    ap.add_argument("--split", default="train", choices=["train", "eval", "all"])
    ap.add_argument("--out", default="data/sft/sft_alpaca.json")
    args = ap.parse_args()

    rows, seen = [], set()
    for path in args.problems:
        for p in rtl_common.load_problems(path):
            if p["split"] != args.split or p["task_id"] in seen:
                continue
            seen.add(p["task_id"])
            rows.append({
                "instruction": rtl_common.prompt_text(p),
                "input": "",
                "output": f"<answer>\n{p['module']}\n</answer>",
            })
    if not rows:
        raise SystemExit("没有题目（检查 --split 与输入文件）")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    lens = [len(r["output"]) for r in rows]
    print(f"[to_llamafactory] {len(rows)} 条 → {args.out} "
          f"(output 长度 {min(lens)}-{max(lens)} 字符)")
    print("[to_llamafactory] 在 LLaMA-Factory 里注册: 见 configs/sft/dataset_info.json")


if __name__ == "__main__":
    main()
