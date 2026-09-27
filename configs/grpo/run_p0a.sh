#!/usr/bin/env bash
# P0a: GRPO 拆分奖励消融 | split_reward=+0.3(综合)/+0.7(仿真) | 独立实验目录
# 控制变量与 E3 完全一致：e2-sft-merged 起点、66 步（total_epochs=6）、
# 其余超参同 run_grpo.sh；唯一差异 = 奖励拆分开关。
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
    +reward.custom_reward_function.reward_kwargs.split_reward=True
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
    trainer.experiment_name=e3-p0a-split-reward
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
