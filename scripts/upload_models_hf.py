# -*- coding: utf-8 -*-
"""upload_models_hf.py — code-r1 实验模型备份上传到 HF（实例上运行）。

顺序：先传「要删的」（e5、e9p2），再传其余（e9p3、e7、verifier）——前两个
传完校验过，本地才允许删除腾空间。走 HF_ENDPOINT=hf-mirror.com（AutoDL 直连
HF 被重置，实测镜像上传可用）。upload_folder 幂等，中断重跑可续传。

用法（实例上）：
  HF_TOKEN=xxx nohup python /root/autodl-tmp/rtl-rlvr/scripts/upload_models_hf.py \
      > /root/autodl-tmp/hf_upload.log 2>&1 < /dev/null &
  tail -f /root/autodl-tmp/hf_upload.log
"""
import os
import sys
import time

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# PITFALLS：hf-mirror 的 Xet 后端（cas-bridge.xethub.hf.co）上传会挂死，
# 必须禁用走传统 LFS presigned 上传（大文件走 S3，实测 S3 可达）
os.environ["HF_HUB_DISABLE_XET"] = "1"

from huggingface_hub import HfApi  # noqa: E402

TOKEN = os.environ["HF_TOKEN"]  # 只从环境变量读，避免密钥入库

MODELS = [
    # (标签, 本地目录, HF repo)——前两个是「先传完先删」的对象
    ("e5-final-3b", "/root/autodl-tmp/models/e5-final-3b",
     "wang072266/code-r1-e5-final-3b"),
    ("e9-phase2-final", "/root/autodl-tmp/models/e9-phase2-final",
     "wang072266/code-r1-e9-phase2-final"),
    ("e9-phase3-final", "/root/autodl-tmp/models/e9-phase3-final",
     "wang072266/code-r1-e9-phase3-final"),
    ("e7-final-3b", "/root/autodl-tmp/models/e7-final-3b",
     "wang072266/code-r1-e7-final-3b"),
    ("verifier-1.5b", "/root/autodl-tmp/models/verifier-1.5b",
     "wang072266/code-r1-verifier-1.5b"),
]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def verify(api, repo, folder):
    local_files = sorted(
        os.path.relpath(os.path.join(dp, f), folder).replace("\\", "/")
        for dp, _, fns in os.walk(folder) for f in fns)
    remote = set(api.list_repo_files(repo, repo_type="model"))
    missing = [f for f in local_files if f not in remote]
    if missing:
        log(f"  ✗ {repo} 缺 {len(missing)} 个文件: {missing[:5]}")
        return False
    log(f"  ✓ {repo} 校验通过（{len(local_files)} 个文件齐全）")
    return True


def main():
    api = HfApi(token=TOKEN)
    log(f"whoami: {api.whoami()['name']}")
    ok_repos = []
    for name, folder, repo in MODELS:
        if not os.path.isdir(folder):
            log(f"SKIP {name}（目录不存在）")
            continue
        marker = f"/root/autodl-tmp/hf_uploaded_{name}.ok"
        if os.path.exists(marker):
            log(f"SKIP {name}（已上传校验过，marker 在）")
            continue
        log(f"=== 开始上传 {name} → {repo} ===")
        t0 = time.time()
        for attempt in range(3):
            try:
                api.create_repo(repo, repo_type="model", exist_ok=True)
                api.upload_folder(folder_path=folder, repo_id=repo,
                                  repo_type="model")
                break
            except Exception as e:
                log(f"  attempt {attempt + 1} failed: {str(e)[:200]}")
                if attempt == 2:
                    log(f"  ✗ {name} 三次失败，跳过（可重跑本脚本续传）")
                    break
                time.sleep(30)
        else:
            continue
        elapsed = time.time() - t0
        if verify(api, repo, folder):
            log(f"=== {name} DONE（{elapsed / 60:.1f} min）===")
            open(f"/root/autodl-tmp/hf_uploaded_{name}.ok", "w").close()
            ok_repos.append((name, folder, repo))
        else:
            log(f"  ✗ {name} 校验失败，不要删本地！重跑脚本")
    log(f"ALL_DONE。校验通过的 repo: {[r for _, _, r in ok_repos]}")


if __name__ == "__main__":
    main()
