# -*- coding: utf-8 -*-
"""parse_training_log.py — veRL 训练日志 → 结构化指标 jsonl + 训练曲线图。

从 veRL console logger 的 step:N 行提取 key=value 指标（ANSI 码剥掉、
"[repeated Nx across cluster]" 行跳过），产出：
  results/<exp>/training_metrics.jsonl   每步一个 json（全量指标，无损）
  results/<exp>/training_curves.png      关键曲线（reward/KL/熵/梯度/loss/时序）
训练中途可反复运行做快照（增量解析，已存在的 step 跳过）。

用法：
  python scripts/parse_training_log.py --log logs/e3_train.log \
      --out-dir results/e3
（matplotlib 在 llamafactory venv 里：/root/llamafactory-env/bin/python）
"""
import argparse
import json
import os
import re
import sys

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
REPEATED_RE = re.compile(r"\[repeated \d+x across cluster\]")
STEP_RE = re.compile(r"step:(\d+)\s+-\s+(.+)$")


def parse_line(line):
    line = ANSI_RE.sub("", line)
    if REPEATED_RE.search(line):
        return None
    m = STEP_RE.search(line)
    if not m:
        return None
    step = int(m.group(1))
    metrics = {}
    # 形如 "key:value - key:value"；value 可能含负号/科学计数
    for part in m.group(2).split(" - "):
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        key, val = key.strip(), val.strip()
        try:
            if val.startswith("np."):
                val = re.sub(r"^np\.(float64|int64)\((.+)\)$", r"\2", val)
            metrics[key] = float(val) if re.match(r"^-?[\d.]+(e[+-]?\d+)?$", val) else val
        except (ValueError, TypeError):
            metrics[key] = val
    return step, metrics


def load_existing(path):
    rows = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    rows[r["step"]] = r
                except json.JSONDecodeError:
                    continue
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="veRL 训练日志路径")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    metrics_path = os.path.join(args.out_dir, "training_metrics.jsonl")
    rows = load_existing(metrics_path)

    with open(args.log, encoding="utf-8", errors="replace") as f:
        for line in f:
            parsed = parse_line(line)
            if parsed is None:
                continue
            step, metrics = parsed
            if step not in rows:
                rows[step] = {"step": step, **metrics}
    if not rows:
        raise SystemExit("没解析到任何 step 行（日志里还没有 step 或格式不对）")

    steps = sorted(rows)
    with open(metrics_path, "w", encoding="utf-8") as f:
        for s in steps:
            f.write(json.dumps(rows[s], ensure_ascii=False) + "\n")
    print(f"[parse] {len(steps)} 步 → {metrics_path}（step {steps[0]}..{steps[-1]}）")

    # ---- 绘图 ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[parse] matplotlib 不可用，跳过绘图（用 llamafactory venv 跑本脚本）")
        return 0

    panels = [
        ("critic/score/mean", "reward mean", None),
        ("critic/score/max", "reward max", None),
        ("critic/score/min", "reward min", None),
        ("rollout_corr/kl", "rollout KL", None),
        ("actor/entropy", "entropy", None),
        ("actor/grad_norm", "grad norm", None),
        ("actor/loss", "actor loss", None),
        ("response_length/mean", "response len", None),
        ("timing_s/step", "sec/step", None),
    ]
    # 验证集指标（若有）：val-aux/rtl-spec/reward/mean@1 补进 reward 图
    val_key = "val-aux/rtl-spec/reward/mean@1"
    fig, axes = plt.subplots(3, 3, figsize=(16, 10))
    for ax, (key, label, _) in zip(axes.flat, panels):
        xs, ys = [], []
        for s in steps:
            if key in rows[s] and isinstance(rows[s][key], (int, float)):
                xs.append(s)
                ys.append(rows[s][key])
        if xs:
            ax.plot(xs, ys, marker=".", ms=3)
        ax.set_title(label)
        ax.set_xlabel("step")
        ax.grid(alpha=0.3)
    # val reward 叠加到第一张图
    vx, vy = [], []
    for s in steps:
        if val_key in rows[s] and isinstance(rows[s][val_key], (int, float)):
            vx.append(s)
            vy.append(rows[s][val_key])
    if vx:
        axes.flat[0].plot(vx, vy, marker="x", ms=5, color="tab:orange",
                          label="val reward")
        axes.flat[0].legend()
    fig.suptitle(f"RTL-RLVR E3 training curves ({len(steps)} steps)")
    fig.tight_layout()
    png = os.path.join(args.out_dir, "training_curves.png")
    fig.savefig(png, dpi=110)
    print(f"[parse] 曲线图 → {png}")

    # 关键数字摘要（诚实：直接打印最新一步与最佳步）
    last = rows[steps[-1]]
    best = max(rows.values(), key=lambda r: r.get("critic/score/mean", -1))
    print(f"[parse] 最新 step {steps[-1]}: reward_mean={last.get('critic/score/mean')} "
          f"kl={last.get('rollout_corr/kl')} entropy={last.get('actor/entropy')}")
    print(f"[parse] 最高 reward_mean 步 {best['step']}: "
          f"{best.get('critic/score/mean')}")
    return 0


if __name__ == "__main__":
    main()
