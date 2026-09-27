# -*- coding: utf-8 -*-
"""sft_hf_fallback.py — LLaMA-Factory 装不上时的保底 LoRA SFT（transformers+PEFT）。

与 llamafactory_sft.yaml 等价：Qwen2.5-Coder-3B-Instruct + LoRA rank 32 /
alpha 64，alpaca 数据（instruction→output），3 epochs，bf16。
诚实纪律：用了本脚本就在 work-log 里如实记录（主方案是 LLaMA-Factory，JD 点名）。

用法：
  python scripts/sft_hf_fallback.py --problems data/spec_set_50.jsonl \
      --split train --base /root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct \
      --out /root/autodl-tmp/models/e2-sft-merged
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rtl_common


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problems", required=True, nargs="+")
    ap.add_argument("--split", default="train")
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--batch-size", type=int, default=4)
    args = ap.parse_args()

    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              TrainingArguments, Trainer)
    from peft import LoraConfig, get_peft_model

    rows, seen = [], set()
    for path in args.problems:
        for p in rtl_common.load_problems(path):
            if p["split"] != args.split or p["task_id"] in seen:
                continue
            seen.add(p["task_id"])
            rows.append({"instruction": rtl_common.prompt_text(p),
                         "output": f"<answer>\n{p['module']}\n</answer>"})
    print(f"[sft-fallback] {len(rows)} 条训练数据")

    tok = AutoTokenizer.from_pretrained(args.base, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, trust_remote_code=True)
    model.gradient_checkpointing_enable()
    model = get_peft_model(model, LoraConfig(
        r=32, lora_alpha=64, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM"))

    # 用与评估端一致的 chat 模板（含默认 system 提示词）
    texts = [rtl_common.apply_qwen_chat(r["instruction"]) + r["output"] +
             "<|im_end|>" for r in rows]

    class DS(torch.utils.data.Dataset):
        def __init__(self, texts):
            self.enc = [tok(t, truncation=True, max_length=2048,
                            return_tensors="pt") for t in texts]

        def __len__(self):
            return len(self.enc)

        def __getitem__(self, i):
            e = self.enc[i]
            return {"input_ids": e["input_ids"][0],
                    "attention_mask": e["attention_mask"][0],
                    "labels": e["input_ids"][0]}

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=os.path.join(args.out, "trainer_tmp"),
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=4, num_train_epochs=args.epochs,
            learning_rate=args.lr, lr_scheduler_type="cosine", warmup_ratio=0.1,
            bf16=True, logging_steps=5, save_strategy="no"),
        train_dataset=DS(texts))
    trainer.train()

    merged = model.merge_and_unload()
    merged.save_pretrained(args.out, safe_serialization=True)
    tok.save_pretrained(args.out)
    print(f"[sft-fallback] 合并模型已保存 → {args.out}")
    print("下一步: 用 eval_rtl.py pipe 评估 E2（同 E1 口径）")


if __name__ == "__main__":
    main()
