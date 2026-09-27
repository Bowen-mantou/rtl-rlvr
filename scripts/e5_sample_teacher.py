# -*- coding: utf-8 -*-
"""e5_sample_teacher.py — DeepSeek API teacher 轨迹采样（E5 前置，本地零卡时跑）。

对训练题（严格排除评估题——防泄露红线）每题采样 n 条，提示词与训练/评估
格式对齐（spec + 接口契约 + <answer> 标签要求）。输出 completions 格式
jsonl，与 annotate_samples.py / eval_rtl.py 无缝衔接。

用法：
  python scripts/e5_sample_teacher.py --problems <训练题jsonl> \
      --out data/e5/traj_teacher.jsonl --n 2 --limit 30 --api-key sk-xxx
  # --limit 0 = 全部题目；试采用 --limit 30 --n 2
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtl_common

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"  # 不用 reasoner：teacher 要正确率，不要推理链


def call_api(api_key, prompt, temperature=0.7, timeout=180, max_tokens=2048):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode("utf-8"))
            return resp["choices"][0]["message"]["content"], None
        except Exception as e:
            err = str(e)[:150]
            if attempt == 2:
                return None, err
            time.sleep(5 * (attempt + 1))


def sample_one(args, p, sample_idx):
    text = rtl_common.prompt_text(p)
    completion, err = call_api(args.api_key, text, temperature=args.temperature)
    if completion is None:
        print(f"  ✗ {p['task_id']} sample {sample_idx}: {err}")
        return None
    return {"task_id": p["task_id"], "completion": completion,
            "model": MODEL, "sample_idx": sample_idx}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", required=True, nargs="+", help="统一 jsonl（可多个）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0, help="只采前 N 题（试采用）")
    ap.add_argument("--api-key", required=True)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    problems, seen = [], set()
    for path in args.problems:
        for p in rtl_common.load_problems(path):
            # 防泄露红线：只采 train split，评估题一个字都不能进
            if p["split"] != "train" or p["task_id"] in seen:
                continue
            seen.add(p["task_id"])
            problems.append(p)
    problems.sort(key=lambda x: x["task_id"])
    if args.limit:
        # 分层取前 N：按 tier 轮转抽取，保证难题/自建都有覆盖
        by_tier = {}
        for p in problems:
            by_tier.setdefault(p["tier"], []).append(p)
        picked, i = [], 0
        while len(picked) < args.limit and by_tier:
            for tier in sorted(by_tier):
                if i < len(by_tier[tier]):
                    picked.append(by_tier[tier][i])
                if len(picked) >= args.limit:
                    break
            i += 1
        problems = picked[:args.limit]
    print(f"[e5-sample] {len(problems)} 题 × n={args.n}，temperature={args.temperature}")

    tasks = [(p, s) for p in problems for s in range(args.n)]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    out_f = open(args.out, "a", encoding="utf-8")
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(sample_one, args, p, s): (p, s) for p, s in tasks}
        for fut in futs:
            row = fut.result()
            if row:
                out_f.write(json.dumps(row, ensure_ascii=False) + "\n")
                out_f.flush()
                ok += 1
            else:
                fail += 1
    out_f.close()
    print(f"[e5-sample] 完成 {ok} 条，失败 {fail} 条 → {args.out}")
    print("下一步（实例上）：python scripts/annotate_samples.py --problems <训练题> "
          "--completions <本输出> --out data/e5/traj_teacher_annotated.jsonl")


if __name__ == "__main__":
    main()
