#!/usr/bin/env bash
# =====================================================================
# EVOLUTION AI - 京东云 2C4G 服务器一键初始化（Ubuntu 22.04 LTS）
#
# 用法（root 登录新购服务器后）：
#   curl -fsSL <此文件URL> -o bootstrap.sh && bash bootstrap.sh
# 或把本文件上传到服务器后执行：bash server_bootstrap.sh
#
# 完成内容：
#   1. 系统更新 + 基础工具
#   2. 2GB swap（2C4G 跑 PG+Redis+双 uvicorn worker 的安全垫）
#   3. Docker CE + compose 插件（阿里云镜像源）
#   4. Docker registry 加速器（DaoCloud）
#   5. 时区 Asia/Shanghai + 自动安全更新
#
# 执行后继续：《jdcloud_2c4g_checklist.md》第 4 步（拉代码部署）
# =====================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "请用 root 执行" >&2; exit 1
fi

echo '==> [1/5] 系统更新与基础工具'
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release git ufw

echo '==> [2/5] 配置 2GB swap（无 swap 才创建）'
if ! swapon --show | grep -q .; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  sysctl -w vm.swappiness=10
  grep -q 'vm.swappiness' /etc/sysctl.conf || echo 'vm.swappiness=10' >> /etc/sysctl.conf
else
  echo '    已有 swap，跳过'
fi

echo '==> [3/5] 安装 Docker CE（阿里云镜像源）'
if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
else
  echo '    Docker 已安装，跳过'
fi

echo '==> [4/5] Docker 镜像加速器（DaoCloud，注意末尾无斜杠）'
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{ "registry-mirrors": ["https://docker.m.daocloud.io"] }
EOF
systemctl daemon-reload
systemctl restart docker
systemctl enable docker

echo '==> [5/5] 时区与自动安全更新'
timedatectl set-timezone Asia/Shanghai
apt-get install -y unattended-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades || true

echo ''
echo '=== 初始化完成 ==='
docker --version
docker compose version
echo "swap: $(swapon --show --noheadings)"
echo ''
echo '下一步：按 deploy/jdcloud_2c4g_checklist.md 第 4 步拉取代码部署'
