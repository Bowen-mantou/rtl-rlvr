#!/bin/bash
# LLaMA-Factory 一键安装（v2：venv 方案，跳过 conda——.condarc 里 pkgs/free 频道已废弃）
# 全部走国内源：pip 清华镜像（llamafactory 直接 pip 装，不走 GitHub）
set -x
LOG=/root/autodl-tmp/llamafactory_install.log
exec > "$LOG" 2>&1
echo "[$(date +%H:%M:%S)] start"

# 1) 环境（venv 秒建；base python 3.12 满足 llamafactory >=3.8 要求）
rm -rf /root/llamafactory-env
python -m venv /root/llamafactory-env

# 2) pip 安装 llamafactory（PyPI 上有官方包，含全部源码 + CLI；清华源）
/root/llamafactory-env/bin/pip install --upgrade pip --index-url https://pypi.tuna.tsinghua.edu.cn/simple
/root/llamafactory-env/bin/pip install llamafactory --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 3) 验证
echo "[$(date +%H:%M:%S)] done"
/root/llamafactory-env/bin/llamafactory-cli version
/root/llamafactory-env/bin/python -c "
import llamafactory, os
p = os.path.dirname(llamafactory.__file__)
print('package dir:', p)
print('dataset_info.json exists:', os.path.exists(os.path.join(p, 'data', 'dataset_info.json')))
"

