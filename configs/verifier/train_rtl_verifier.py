# -*- coding: utf-8 -*-
"""train_rtl_verifier.py — RTL verifier 训练（E4 可选，Code-R1 E7 方法原样搬）。

任务：6 分类预测「这个 Verilog 模块能通过几个测试（0-5）」，推理时 E[k]/5 = V
  （k = 综合失败记 0；综合过 = 仿真通过测试数；k5 = round(k/N*5) 截断到 [0,5]）
模型：Qwen2.5-1.5B-Instruct（非 Coder 版，降同源盲点 —— 与 E7 相同理由）
校准：温度缩放（网格搜 τ）+ Platt 缩放，ECE < 0.05 验收
数据：scripts/annotate_samples.py 的产物（completions 双闸标注 jsonl）

改编自 03-code-r1/train_verifier.py（E7 实测跑通：2 epochs / bs2×16 / lr 2e-5，
gradient_checkpointing 省显存，1.5B 全参 2048 序列）。

用法：
  python configs/verifier/train_rtl_verifier.py --data data/verifier/verifier_train.jsonl \
      --out /root/autodl-tmp/rtl-rlvr/checkpoints/verifier/e4-verifier-1.5b
"""
import argparse
import json
import math
import os

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
import datasets

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
MAX_LEN = 2048
INSTR = "这个 Verilog 模块能通过几个测试？只回答一个数字 (0-5)。"


def build_input(prompt, code):
    return f"{prompt}\n\n```verilog\n{code}\n```\n\n{INSTR}"


def load_data(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    ds = datasets.Dataset.from_list(rows)
    # k 截断到 [0,5]（N 可能 >5）；N==0 的脏行报错
    for r in rows:
        if r["N"] <= 0:
            raise SystemExit(f"标注数据有 N<=0 的脏行: {r}")
    ds = ds.map(lambda r: {"k5": max(0, min(5, round(r["k"] / r["N"] * 5)))})
    return ds


def tokenize(examples, tok):
    texts = [build_input(p, c) for p, c in zip(examples["prompt"], examples["code"])]
    enc = tok(texts, truncation=True, max_length=MAX_LEN, padding="max_length")
    labels = []
    for i, k in enumerate(examples["k5"]):
        row = [-100] * MAX_LEN
        pos = sum(1 for t in enc["input_ids"][i] if t != tok.pad_token_id) - 1
        row[pos] = tok.convert_tokens_to_ids(str(k))
        labels.append(row)
    enc["labels"] = labels
    return enc


def train(args):
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    ds = load_data(args.data)
    ds = ds.train_test_split(test_size=0.1, seed=42)
    train_ds = ds["train"]
    calib_ds = ds["test"]

    # source 加权（E7 同款机制；默认全 1 = 均匀，可在此改权重）
    train_ds = train_ds.map(lambda r: {"__w": 1.0})
    train_ds = train_ds.map(lambda b: tokenize(b, tok), batched=True,
                            remove_columns=train_ds.column_names)
    calib_enc = calib_ds.map(lambda b: tokenize(b, tok), batched=True)

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.bfloat16, trust_remote_code=True)
    model.gradient_checkpointing_enable()  # 省激活（1.5B 全参 2048 序列必需）

    trainer = Trainer(
        model=model,
        args=TrainingArguments(output_dir=os.path.join(args.out, "trainer_tmp"),
                               per_device_train_batch_size=2,
                               gradient_accumulation_steps=16, learning_rate=2e-5,
                               num_train_epochs=2, bf16=True, save_strategy="no",
                               logging_steps=50, remove_unused_columns=False),
        train_dataset=train_ds,
    )
    trainer.train()
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)

    # ---- 校准（与 E7 相同：温度缩放 + Platt + ECE）----
    import torch.nn.functional as F  # noqa: F401
    model.eval()
    logits_list, labels_list = [], []
    for i in range(0, len(calib_enc), 4):
        idxs = list(range(i, min(i + 4, len(calib_enc))))
        batch_ids = torch.tensor([calib_enc[k]["input_ids"] for k in idxs]).cuda()
        with torch.no_grad():
            out = model(input_ids=batch_ids)
        for j, k in enumerate(idxs):
            lab = calib_enc[k]["labels"]
            pos = next((p for p, v in enumerate(lab) if v != -100), 0)
            logits_list.append(out.logits[j, pos, :].float().cpu().numpy())
        labels_list.extend([calib_ds[k]["k5"] for k in idxs])

    logits = np.array(logits_list)
    labels = np.array(labels_list)
    v_raw = (torch.softmax(torch.tensor(logits), -1).numpy()
             * np.arange(6)).sum(-1) / 5  # E[k]/5

    def temp_calibrate(logit1, tau):
        return 1 / (1 + np.exp(-logit1 / tau))

    logit1 = logits[:, 1] - logits[:, 0]
    best_tau, best_loss = 1.0, float("inf")
    for tau in np.arange(0.5, 2.01, 0.1):
        p = temp_calibrate(logit1, tau)
        loss = log_loss((labels > 0).astype(int), p, labels=[0, 1])
        if loss < best_loss:
            best_tau, best_loss = tau, loss

    platt = LogisticRegression()
    platt.fit(logit1.reshape(-1, 1), (labels > 0).astype(int))
    v_platt = platt.predict_proba(logit1.reshape(-1, 1))[:, 1]

    ece = 0.0
    order = np.argsort(v_platt)
    bins = np.array_split(order, 10)
    for b in bins:
        if len(b) == 0:
            continue
        conf = v_platt[b].mean()
        acc = (labels[b] > 0).mean()
        ece += abs(conf - acc) * len(b)
    ece /= len(labels)

    json.dump({"tau": best_tau, "platt_coef": platt.coef_[0][0],
               "platt_intercept": platt.intercept_[0],
               "ece_platt": float(ece), "ece_tau": float(best_loss),
               "n_calib": len(labels)},
              open(os.path.join(args.out, "calibration.json"), "w"))

    print(f"温度 τ={best_tau:.2f} (log_loss={best_loss:.4f})")
    print(f"Platt a={platt.coef_[0][0]:.3f} b={platt.intercept_[0]:.3f}")
    print(f"ECE(platt)={ece:.4f}  → {'✅ 验收通过' if ece < 0.05 else '❌ 不达标，需重训/换3B'}")
    print(f"校准集 V 均值={v_platt.mean():.3f} std={v_platt.std():.3f}（std<0.1 说明塌缩）")
    print(f"n_calib={len(labels)}（校准集 < 50 条时 ECE 数字参考价值有限，如实报告）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="annotate_samples.py 的产物")
    ap.add_argument("--out", required=True)
    train(ap.parse_args())
