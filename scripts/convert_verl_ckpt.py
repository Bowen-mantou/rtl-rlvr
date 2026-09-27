# -*- coding: utf-8 -*-
"""convert_verl_ckpt.py — veRL FSDP checkpoint → HuggingFace bf16 模型（E3 评估用）。

改编自 Code-R1 项目实测可用的 convert_ckpt.py（同款 veRL main save_contents=
[model,extra] 格式：actor/model_world_size_1_rank_0.pt）。无卡模式 CPU 可跑。

用法：
  python scripts/convert_verl_ckpt.py \
      --ckpt /root/autodl-tmp/checkpoints/rtl-rlvr/e3-grpo-dualgate-3b/global_step_50/actor/model_world_size_1_rank_0.pt \
      --src-model /root/autodl-tmp/models/Qwen2.5-Coder-3B-Instruct \
      --dst /root/autodl-tmp/models/e3-final-3b

提示：veRL 保存的 hf_model 目录是 fp32（12GB），评估直接用本脚本转 bf16。
若实例上已有 Code-R1 的 convert_ckpt.py 也可用，本脚本与其等价。
"""
import argparse
import os
import shutil

import torch
from transformers import AutoModelForCausalLM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True, help="actor/model_world_size_1_rank_0.pt")
    ap.add_argument("--src-model", required=True, help="基座模型目录（tokenizer 来源）")
    ap.add_argument("--dst", required=True)
    args = ap.parse_args()

    sd = torch.load(args.ckpt, map_location="cpu")
    if isinstance(sd, dict) and "model" in sd and isinstance(sd["model"], dict):
        sd = sd["model"]
    print(f"state_dict 张量数: {len(sd)}")

    model = AutoModelForCausalLM.from_pretrained(
        args.src_model, torch_dtype=torch.bfloat16, trust_remote_code=True)
    hf_keys = set(model.state_dict().keys())
    if not hf_keys.issubset(sd.keys()):
        stripped = {}
        for k, v in sd.items():
            nk = k
            for prefix in ("_fsdp_wrapped_module.", "module.", "model."):
                if nk.startswith(prefix):
                    nk = nk[len(prefix):]
                    break
            stripped[nk] = v
        sd = stripped
    missing = hf_keys - sd.keys()
    unexpected = sd.keys() - hf_keys
    print(f"missing: {len(missing)} | unexpected: {len(unexpected)}")
    if missing:
        raise SystemExit(f"state_dict 缺键，转换失败: {sorted(missing)[:5]}")

    model.load_state_dict(sd)
    model.save_pretrained(args.dst)
    for f in os.listdir(args.src_model):
        if not f.endswith(".safetensors"):
            src, dst = os.path.join(args.src_model, f), os.path.join(args.dst, f)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fns in os.walk(args.dst) for f in fns) / 1e9
    print(f"已转换 → {args.dst}（{size:.2f} GB）")


if __name__ == "__main__":
    main()
