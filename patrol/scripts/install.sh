#!/bin/bash
# Patrol Inspection System - Installation Script
# 运维巡检平台部署脚本

set -e

echo "================================================"
echo "  Patrol 巡检系统 - 安装部署脚本"
echo "================================================"

# Get project root directory
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo ""
echo "[1/5] 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.8+"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Python $PYTHON_VERSION 已安装"

echo ""
echo "[2/5] 安装Python依赖..."
python3 -m pip install --upgrade pip -q
python3 -m pip install -r requirements.txt -q
echo "  Python依赖安装完成"

echo ""
echo "[3/5] 构建前端界面..."
if command -v node &> /dev/null && command -v npm &> /dev/null; then
    echo "  发现Node.js，开始构建前端..."
    cd web
    npm install --silent 2>/dev/null || npm install
    npm run build 2>/dev/null || {
        echo "  WARNING: 前端构建失败，将使用后端仅API模式"
        mkdir -p dist
        echo '<!DOCTYPE html><html><body><h1>Patrol API Running</h1><p>Frontend build failed. Use API directly.</p></body></html>' > dist/index.html
    }
    cd "$PROJECT_DIR"
    echo "  前端构建完成"
else
    echo "  WARNING: Node.js未安装，跳过前端构建"
    echo "  您可以在有Node环境的机器上构建后拷贝 web/dist 目录"
    mkdir -p web/dist
    echo '<!DOCTYPE html><html><body><h1>Patrol API Running</h1><p>Frontend not built. Please run npm build in web/ directory.</p></body></html>' > web/dist/index.html
fi

echo ""
echo "[4/5] 初始化数据库..."
python3 -c "
import app
app.init_db()
print('  数据库初始化完成')
"

echo ""
echo "[5/5] 创建启动脚本..."
cat > start.sh << 'SCRIPT'
#!/bin/bash
cd "$(dirname "$0")"
echo "Starting Patrol Inspection System..."
echo "Web UI: http://0.0.0.0:5000"
echo "API:    http://0.0.0.0:5000/api"
python3 app.py
SCRIPT
chmod +x start.sh

echo ""
echo "================================================"
echo "  安装完成！"
echo "================================================"
echo ""
echo "启动方式:"
echo "  ./start.sh              # 开发模式启动"
echo "  nohup ./start.sh &      # 后台运行"
echo ""
echo "访问地址:"
echo "  http://localhost:5000"
echo ""