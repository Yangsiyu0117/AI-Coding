#!/bin/bash
# Patrol Offline Build Script
# 离线打包脚本 - 将所有依赖打包，便于内网环境部署

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build/patrol-offline"
VERSION=$(grep 'version' "$PROJECT_DIR/config.yaml" 2>/dev/null || echo "v1.0.0")

echo "Building offline package for Patrol $VERSION..."

# Clean
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy source
cp -r "$PROJECT_DIR/app.py" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/core" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/plugins" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/notifiers" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/templates" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/config.yaml" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/requirements.txt" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/scripts/install.sh" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/scripts/patrol_cron.sh" "$BUILD_DIR/"
cp -r "$PROJECT_DIR/Makefile" "$BUILD_DIR/"

# Build frontend
if [ -d "$PROJECT_DIR/web" ]; then
    cd "$PROJECT_DIR/web"
    npm install --silent
    npm run build
    cp -r dist "$BUILD_DIR/web/"
    cd "$PROJECT_DIR"
fi

# Download Python packages
pip3 download -r "$PROJECT_DIR/requirements.txt" -d "$BUILD_DIR/packages" --quiet 2>/dev/null || {
    echo "  WARNING: Could not download all packages (offline bundle will need internet)"
    mkdir -p "$BUILD_DIR/packages"
}

# Create offline install script
cat > "$BUILD_DIR/offline_install.sh" << 'SCRIPT'
#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "Offline installing Patrol..."

# Install from local packages
pip3 install --no-index --find-links=packages -r requirements.txt 2>/dev/null || {
    echo "Trying online install..."
    pip3 install -r requirements.txt
}

# Build frontend
if [ -d "web" ] && [ ! -f "web/dist/index.html" ]; then
    cd web
    npm install --silent
    npm run build
    cd ..
fi

# Init DB
python3 -c "import app; app.init_db()"

echo "Install complete! Run: python3 app.py"
SCRIPT
chmod +x "$BUILD_DIR/offline_install.sh"

# Create tarball
cd "$PROJECT_DIR/build"
tar czf "patrol-offline.tar.gz" "patrol-offline/"
rm -rf "patrol-offline"

echo ""
echo "Offline package created: build/patrol-offline.tar.gz"
echo "Size: $(du -h build/patrol-offline.tar.gz | cut -f1)"