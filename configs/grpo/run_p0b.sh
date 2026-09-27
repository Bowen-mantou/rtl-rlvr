#!/usr/bin/env bash
# P0b: 二值奖励 + n=8 + DAPO 组过滤 | 独立实验目录
# split_reward 已在 P0a 证伪（全口径落败），奖励保持二值与 E3 一致；
# 与 E3 差异 = n=8 + filter_groups（调研背书：组大小 4→8 +4.2pp、
# 组过滤直击难题全错组零梯度）。起点 e2-sft-merged、66 步同 E3。
set -xeuo pipefail
export VERL_USE_UV=0
export PYTHONPATH=/root/autodl-tmp
export LD_LIBRARY_PATH=/root/miniconda3/lib/python3.12/site-packages/nvidia/cu13/lib:${LD_LIBRARY_PATH:-}

MODEL_PATH=/root/autodl-tmp/models/e2-sft-merged
if [ ! -d "$MODEL_PATH" ]; then
  echo "FATAL: P0a 初始化模型不存在: $MODEL_PATH"
  exit 1
fi
TRAIN_FILE=/root/autodl-tmp/rtl-rlvr/data/grpo/train.parquet
TEST_FILE=/root/autodl-tmp/rtl-rlvr/data/grpo/val.parquet

DATA=(
    algorithm.adv_estimator=grpo
    algorithm.filter_groups.enable=True
    # metric 必须是 acc：本版 veRL naive manager 对 float 返回自动写
    # reward_extra_info["acc"]=score（实测 "score" 键不存在会崩）
    algorithm.filter_groups.metric=acc
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
    actor_rollout_ref.rollout.n=8
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
    trainer.experiment_name=e3-p0b-split-n8-filter
    trainer.n_gpus_per_node=1
    trainer.nnodes=1
    trainer.save_freq=12
    trainer.max_actor_ckpt_to_keep=1
    trainer.test_freq=6
    trainer.total_epochs=6
)

python3 -m verl.trainer.main_ppo \
    "${DATA[@]}" \
    "${MODEL[@]}" \
    "${ACTOR[@]}" \
    "${ROLLOUT[@]}" \
    "${REF[@]}" \
    "${TRAINER[@]}" \
    "$@"
