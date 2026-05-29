#!/bin/bash
set -euo pipefail
# ============================================================
# setup.sh — Deploy Platform 一键部署脚本
# 用法: chmod +x setup.sh && sudo bash setup.sh
# 说明: 将此脚本放在解压后的 deploy-platform-v*/ 目录下运行
# ============================================================

INSTALL_DIR="/opt/deploy-platform"
CONDA_DIR="/opt/miniconda3"
CONDA_ENV="deploy-platform"
APP_PORT="${APP_PORT:-8000}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------- 1. 检查运行目录 ----------
if [[ ! -d "./backend/app" ]] || [[ ! -d "./frontend/dist" ]]; then
    log_error "请在解压后的部署包根目录下运行此脚本（需包含 backend/ 和 frontend/dist/）"
    exit 1
fi

log_info "开始部署 Deploy Platform..."

# ---------- 2. 安装 Miniconda（如未安装） ----------
if [[ ! -x "$CONDA_DIR/bin/conda" ]]; then
    log_info "Miniconda 未安装，正在下载..."
    INSTALLER="/tmp/miniconda_$$.sh"
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    if command -v curl &>/dev/null; then
        curl -sL -o "$INSTALLER" "$MINICONDA_URL"
    elif command -v wget &>/dev/null; then
        wget -q -O "$INSTALLER" "$MINICONDA_URL"
    else
        log_error "需要 curl 或 wget 下载 Miniconda，请先安装其中之一"
        exit 1
    fi
    bash "$INSTALLER" -b -p "$CONDA_DIR"
    rm -f "$INSTALLER"
    "$CONDA_DIR/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main 2>/dev/null || true
    "$CONDA_DIR/bin/conda" tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r 2>/dev/null || true
    log_info "Miniconda 安装完成: $($CONDA_DIR/bin/python --version)"
else
    log_info "Miniconda 已存在: $($CONDA_DIR/bin/python --version)"
fi

# ---------- 3. 创建 Python 环境 ----------
if ! "$CONDA_DIR/bin/conda" env list | grep -q "^${CONDA_ENV} "; then
    log_info "创建 Python 3.11 环境: $CONDA_ENV..."
    "$CONDA_DIR/bin/conda" create -n "$CONDA_ENV" python=3.11 -y
else
    log_info "Conda 环境 $CONDA_ENV 已存在"
fi

# ---------- 4. 复制文件 ----------
log_info "部署文件到 $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"/{data,uploads,logs,frontend/dist}
rm -rf "$INSTALL_DIR/backend" "$INSTALL_DIR/frontend/dist"

# 后端（排除不需要的文件）
cp -r ./backend "$INSTALL_DIR/backend"
find "$INSTALL_DIR/backend" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "$INSTALL_DIR/backend" -name '*.pyc' -delete 2>/dev/null || true
rm -f "$INSTALL_DIR/backend/.env" 2>/dev/null || true
rm -rf "$INSTALL_DIR/backend/tests" 2>/dev/null || true
rm -rf "$INSTALL_DIR/backend/uploads" 2>/dev/null || true
rm -f "$INSTALL_DIR/backend"/*.db 2>/dev/null || true

# 前端构建产物
cp -r ./frontend/dist "$INSTALL_DIR/frontend/dist"

# ---------- 5. 创建 .env（如果不存在） ----------
if [[ ! -f "$INSTALL_DIR/backend/.env" ]]; then
    SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-f0-9' | head -c64 || echo "change-me-$(date +%s)")
    cat > "$INSTALL_DIR/backend/.env" << EOF
APP_DATABASE_URL=sqlite:////opt/deploy-platform/data/deploy_platform.db
APP_JWT_SECRET_KEY=${SECRET_KEY}
APP_UPLOAD_DIR=/opt/deploy-platform/uploads
APP_LOG_DIR=/opt/deploy-platform/logs
APP_SSH_DEFAULT_TIMEOUT=10
APP_DEBUG=false
EOF
    log_info "已生成 .env 配置文件（JWT 密钥已随机生成）"
else
    log_info ".env 已存在，跳过创建"
fi

# ---------- 6. 安装依赖 ----------
log_info "安装 Python 依赖..."
"$CONDA_DIR/bin/conda" run -n "$CONDA_ENV" pip install -r "$INSTALL_DIR/backend/requirements.txt" -q

# ---------- 7. 初始化数据库 ----------
log_info "初始化数据库..."
cd "$INSTALL_DIR/backend"
"$CONDA_DIR/bin/conda" run -n "$CONDA_ENV" alembic upgrade head 2>&1 | tail -3

# ---------- 8. 配置 systemd 服务 ----------
SERVICE_FILE="/etc/systemd/system/deploy-platform.service"
if [[ ! -f "$SERVICE_FILE" ]]; then
    log_info "创建 systemd 服务..."
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Deploy Platform
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/backend
ExecStart=$CONDA_DIR/bin/conda run -n $CONDA_ENV uvicorn app.main:app --host 0.0.0.0 --port $APP_PORT
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable deploy-platform
    log_info "systemd 服务已创建并启用"
else
    log_info "systemd 服务已存在，重新加载配置..."
    systemctl daemon-reload
fi

# ---------- 9. 启动服务 ----------
log_info "启动服务..."
systemctl restart deploy-platform
sleep 3

if systemctl is-active --quiet deploy-platform; then
    log_info "========================================="
    log_info "  部署成功！"
    log_info "  访问地址: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '<server-ip>'):${APP_PORT}"
    log_info "  首次使用请注册管理员账户"
    log_info "========================================="
else
    log_error "服务启动失败，请检查日志: journalctl -u deploy-platform -n 30"
    exit 1
fi
