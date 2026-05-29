#!/bin/bash
set -euo pipefail
# ============================================================
# package.sh — 打包部署包（在开发机器上执行）
# 用法: bash package.sh
# 输出: deploy-platform-vX.Y.Z.tar.gz
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VERSION=$(grep 'app_version' backend/app/config.py | cut -d'"' -f2 | head -1)
PACKAGE_NAME="deploy-platform-v${VERSION}"
BUILD_DIR="/tmp/${PACKAGE_NAME}"

echo "=== 打包 Deploy Platform v${VERSION} ==="

# 1. 构建前端
echo "[1/4] 构建前端..."
cd frontend
npm run build 2>&1 | tail -1
cd "$SCRIPT_DIR"

# 2. 创建打包目录
echo "[2/4] 创建打包目录..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/{backend,frontend/dist}

# 3. 复制文件
echo "[3/4] 复制文件..."

# 后端（排除不需要的文件）
rsync -a \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='*.db' \
    --exclude='.env' --exclude='tests' --exclude='uploads' \
    --exclude='venv' --exclude='.venv' --exclude='.pytest_cache' \
    backend/ "$BUILD_DIR/backend/"

# 前端构建产物
rsync -a frontend/dist/ "$BUILD_DIR/frontend/dist/"

# 部署脚本
cp setup.sh "$BUILD_DIR/"

# 使用说明
cat > "$BUILD_DIR/README.txt" << 'EOF'
Deploy Platform - 部署包
================================

部署步骤：

1. 将此 tar.gz 包上传到服务器
   scp deploy-platform-v*.tar.gz root@<server>:/tmp/

2. 在服务器上解压
   tar xzf /tmp/deploy-platform-v*.tar.gz -C /tmp/

3. 进入目录，运行部署脚本
   cd /tmp/deploy-platform-v*
   sudo bash setup.sh

4. 访问平台
   http://<server-ip>:8000

5. 首次使用需要注册管理员账户（第一个注册的用户自动为管理员）

注意事项：
- 需要 root 权限（systemd 服务配置 + /opt 写入）
- 需要访问外网（下载 Miniconda 和 Python 包）
- 如果服务器已有 Miniconda，会自动跳过安装
- 升级部署只需重新解压覆盖并运行 setup.sh 即可
EOF

# 4. 打包
echo "[4/4] 打包..."
cd /tmp
tar czf "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}/"
mv "${PACKAGE_NAME}.tar.gz" "$SCRIPT_DIR/"
rm -rf "$BUILD_DIR"

echo ""
echo "========================================="
echo "  打包完成: ${SCRIPT_DIR}/${PACKAGE_NAME}.tar.gz"
echo "  大小: $(du -sh "$SCRIPT_DIR/${PACKAGE_NAME}.tar.gz" | cut -f1)"
echo "========================================="
echo ""
echo "部署方式："
echo "  1. 将包传到服务器"
echo "  2. tar xzf ${PACKAGE_NAME}.tar.gz -C /tmp/"
echo "  3. cd /tmp/${PACKAGE_NAME} && sudo bash setup.sh"
