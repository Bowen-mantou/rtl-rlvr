#!/usr/bin/env bash
# E3: GRPO 双闸奖励 | Qwen2.5-Coder-3B-Instruct 全参 | FSDP + vLLM
# 超参沿用 Code-R1 E1 实测定稿（run_e1.sh）：n=4, lr 1e-6, kl 0.001 low_var_kl,
# micro 4, ppo_max_token_len 4096, save_contents=[model,extra]
#
# 步数账：94 题（自建 40 + VerilogEval 62，减 val 8）/ batch 8 ≈ 12 步/epoch
# 首轮 66 步（total_epochs=6）reward 未到平台期（最高出现在 step 55），
# 续训用 resume_mode=auto + total_epochs=12 → 总 132 步。
#
# 用法：
#   cd /root/autodl-tmp && bash rtl-rlvr/configs/grpo/run_grpo.sh
#   # 必须在数据盘 cwd 启动（PITFALLS：veRL 启动 cwd 决定 checkpoint 写哪块盘）
#
# 可选开关（设计文档加分设计，默认关；E3b/E3c 单独验证时加在命令行末尾）：
#   +reward.custom_reward_function.reward_kwargs.split_reward=True   # E3b 拆两段 +0.3/+0.7
#   +reward.custom_reward_function.reward_kwargs.lint_bonus=True     # E3c lint 行为奖励
#
# 卡型适配：
#   6000D-84G（Code-R1 实例，本配置实测同款）：直接用
#   2×4090-24G（新租卡）：micro 4→2、gpu_memory_utilization 0.25→0.30、
#     ppo_max_token_len_per_gpu 4096→2048、log_prob 2→1；
#     若仍 OOM 再加 actor_rollout_ref.actor.fsdp_config.optimizer_offload=True
set -xeuo pipefail
export VERL_USE_UV=0
export PYTHONPATH=/root/autodl-tmp
# 6000D 实例：vLLM EngineCore workers 需要 cu13 运行库（新租 4090 实例可注释掉）
export LD_LIBRARY_PATH=/root/miniconda3/lib/python3.12/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}

# E3 = E2 + GRPO（设计文档第五节）：初始化必须是 SFT 合并模型，不是原始基座
# 2026-09-20 事故：曾误指原始基座白跑 36 步 —— 契约断言防复发
MODEL_PATH=/root/autodl-tmp/models/e2-sft-merged
if [ ! -d "$MODEL_PATH" ]; then
  echo "FATAL: E3 初始化模型不存在: $MODEL_PATH（先跑 E2 SFT + 合并，见 configs/sft/命令清单.md）"
  exit 1
fi
TRAIN_FILE=/root/autodl-tmp/rtl-rlvr/data/grpo/train.parquet
TEST_FILE=/root/autodl-tmp/rtl-rlvr/data/grpo/val.parquet

DATA=(
    algorithm.adv_estimator=grpo
    data.train_files=${TRAIN_FILE}
    data.val_files=${TEST_FILE}
    data.train_batch_size=8
    data.val_batch_size=8
    data.max_prompt_length=1024
    data.max_response_length=1024
    data.filter_overlong_prompts=True
    data.truncation=left
    algorithm.use_kl_in_reward=False
    reward.custom_reward_function.path=/root/autodl-tmp/rtl-rlvr/configs/grpo/reward_fn.py
    reward.custom_reward_function.name=compute_score
)

MODEL=(
    actor_rollout_ref.model.path=${MODEL_PATH}
    actor_rollout_ref.model.use_remove_padding=True
    actor_rollout_ref.model.enable_gradient_checkpointing=True
)

ACTOR=(
    actor_rollout_ref.actor.optim.lr=1e-6
    actor_rollout_ref.actor.ppo_mini_batch_size=32
    actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=4
    actor_rollout_ref.actor.use_kl_loss=True
    actor_rollout_ref.actor.kl_loss_coef=0.001
    actor_rollout_ref.actor.kl_loss_type=low_var_kl
    actor_rollout_ref.actor.entropy_coeff=0
    actor_rollout_ref.actor.fsdp_config.param_offload=False
    actor_rollout_ref.actor.fsdp_config.optimizer_offload=False
    actor_rollout_ref.actor.ppo_max_token_len_per_gpu=4096
    actor_rollout_ref.actor.use_dynamic_bsz=True
    actor_rollout_ref.actor.checkpoint.save_contents=[model,extra]
)

ROLLOUT=(
    actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=2
    actor_rollout_ref.rollout.tensor_model_parallel_size=1
    actor_rollout_ref.rollout.name=vllm
    +actor_rollout_ref.rollout.enable_sleep_mode=False
    actor_rollout_ref.rollout.gpu_memory_utilization=0.25
    actor_rollout_ref.rollout.enforce_eager=False
    actor_rollout_ref.rollout.free_cache_engine=True
    actor_rollout_ref.rollout.log_prob_use_dynamic_bsz=True
    actor_rollout_ref.rollout.log_prob_max_token_len_per_gpu=8192
    actor_rollout_ref.rollout.n=4
)

REF=(
    actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=2
    actor_rollout_ref.ref.fsdp_config.param_offload=True
    actor_rollout_ref.ref.log_prob_use_dynamic_bsz=True
    actor_rollout_ref.ref.log_prob_max_token_len_per_gpu=8192
)

TRAINER=(
    trainer.critic_warmup=0
    trainer.logger='["console"]'
    trainer.project_name=rtl-rlvr
    trainer.experiment_name=e3-grpo-dualgate-3b
    trainer.n_gpus_per_node=1
    trainer.nnodes=1
    trainer.save_freq=12
    trainer.max_actor_ckpt_to_keep=1
    trainer.test_freq=6
    trainer.total_epochs=12
    trainer.resume_mode=auto
)

python3 -m verl.trainer.main_ppo \
    "${DATA[@]}" \
    "${MODEL[@]}" \
    "${ACTOR[@]}" \
    "${ROLLOUT[@]}" \
    "${REF[@]}" \
    "${TRAINER[@]}" \
    "$@"
