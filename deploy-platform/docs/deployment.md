# Deploy Platform — 运维升级发布平台 — 部署步骤

> **适用版本**: v0.5.1 | **最后更新**: 2026-05-29

---

## 一、环境要求

| 项目 | 最低要求 |
|------|---------|
| 操作系统 | RHEL/CentOS 8+, Ubuntu 20.04+ |
| Python | 3.11+ |
| Node.js | 18+（仅开发机构建前端需要） |
| 内存 | 2 GB+ |
| 磁盘 | 10 GB+（含上传包空间） |
| 网络 | 可访问 PyPI（安装 Python 依赖）；目标服务器需 SSH 可达 |

---

## 二、部署方式一：setup.sh 一键部署（推荐）

项目根目录提供了 `setup.sh` 自动化部署脚本，适用于内网环境（无 Docker）。

### 2.1 构建前端

在开发机器上：

```bash
cd frontend
npm install
npm run build
```

### 2.2 打包项目

```bash
# 使用打包脚本
bash package.sh

# 生成 deploy-platform-v0.5.1.tar.gz
```

### 2.3 上传并执行部署

```bash
# 上传到服务器
scp deploy-platform-v0.5.1.tar.gz root@<your-server-ip>:/tmp/

# SSH 到服务器
ssh root@<your-server-ip>

# 解压并部署
cd /tmp
tar xzf deploy-platform-v0.5.1.tar.gz
cd deploy-platform-v0.5.1
bash setup.sh
```

### 2.4 setup.sh 做了什么

1. 安装 Miniconda 到 `/opt/miniconda3`（如已安装则跳过）
2. 创建 Python 3.11 conda 环境 `deploy-platform`
3. 将后端代码复制到 `/opt/deploy-platform/backend/`
4. 将前端产物复制到 `/opt/deploy-platform/frontend/dist/`
5. 生成 `.env` 文件（含随机 JWT 密钥）
6. 安装 Python 依赖 `pip install -r requirements.txt`
7. 运行数据库迁移 `alembic upgrade head`
8. 创建 systemd 服务 `/etc/systemd/system/deploy-platform.service`
9. 启动服务并设为开机自启

### 2.5 验证部署

```bash
# 健康检查
curl http://localhost:8000/health
# 返回: {"status": "ok"}

# 前端页面
curl http://localhost:8000/
# 返回: HTML 页面

# 查看服务状态
systemctl status deploy-platform
```

首次使用：访问 `http://<服务器IP>:8000`，在登录页点击注册，**第一个注册的用户自动成为管理员**。

---

## 三、部署方式二：手动部署

适用于需要自定义路径或已有 Python 环境的场景。

### 3.1 安装 Python 环境

```bash
# 方式 A: Miniconda
curl -o /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash /tmp/miniconda.sh -b -p /opt/miniconda3
/opt/miniconda3/bin/conda create -n deploy-platform python=3.11 -y
```

### 3.2 创建目录结构

```bash
mkdir -p /opt/deploy-platform/{backend,frontend/dist,data,uploads}
```

### 3.3 部署后端

```bash
# 复制后端代码到服务器
cd /opt/deploy-platform/backend

# 安装依赖
/opt/miniconda3/bin/conda run -n deploy-platform pip install -r requirements.txt

# 创建 .env 配置文件
cat > .env << 'EOF'
APP_DATABASE_URL=sqlite:////opt/deploy-platform/data/deploy_platform.db
APP_JWT_SECRET_KEY=<使用 openssl rand -hex 32 生成>
APP_UPLOAD_DIR=/opt/deploy-platform/uploads
APP_LOG_DIR=/opt/deploy-platform/logs
APP_DEBUG=false
EOF

# 初始化数据库
/opt/miniconda3/bin/conda run -n deploy-platform alembic upgrade head
```

### 3.4 部署前端

```bash
# 将前端 dist/ 目录复制到服务器
# 从开发机器:
tar czf - frontend/dist/ | ssh root@<server> 'cd /opt/deploy-platform && tar xzf -'
```

### 3.5 创建 systemd 服务

```bash
cat > /etc/systemd/system/deploy-platform.service << 'EOF'
[Unit]
Description=Deploy Platform
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/deploy-platform/backend
ExecStart=/opt/miniconda3/bin/conda run -n deploy-platform uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now deploy-platform
```

---

## 四、部署方式三：Docker Compose

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

三个持久卷：`deploy_data`（数据库）、`deploy_uploads`（升级包）、`deploy_logs`（日志）。

---

## 五、环境变量配置

所有环境变量使用 `APP_` 前缀，在 `backend/.env` 中配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_APP_NAME` | Deploy Platform | 应用名称 |
| `APP_APP_BRAND` | (空) | 品牌缩写，显示在 Logo 处 |
| `APP_APP_TITLE` | 运维升级发布平台 | 页面标题 |
| `APP_DATABASE_URL` | sqlite:///... | 数据库连接（支持 PostgreSQL） |
| `APP_JWT_SECRET_KEY` | change-me-in-production | JWT 密钥，**生产必改** |
| `APP_JWT_EXPIRE_MINUTES` | 480 | Token 过期时间(分钟) |
| `APP_UPLOAD_DIR` | ./uploads | 升级包存储目录 |
| `APP_LOG_DIR` | ../logs | 日志目录 |
| `APP_MAX_UPLOAD_SIZE_MB` | 500 | 最大上传文件大小 |
| `APP_ALLOWED_UPLOAD_EXTENSIONS` | [.tar.gz,.zip,.tgz,.gz,.bin] | 允许的文件扩展名 |
| `APP_REMOTE_UPDATE_BASE` | /opt/update | 远程服务器升级目录 |
| `APP_SSH_DEFAULT_TIMEOUT` | 10 | SSH 连接超时(秒) |
| `APP_DEBUG` | true | 调试模式 |

> **注意**：`app_brand`、`app_title`、`max_upload_size_mb`、`allowed_upload_extensions`、`remote_update_base` 也可以在平台前端的「系统设置 → 平台设置」页面中直接修改，保存后立即生效。

---

## 六、平台配置（运行时修改）

平台支持两类可在线修改的配置：

### 6.1 平台设置（系统设置 → 平台设置）

| 配置项 | 说明 |
|--------|------|
| 品牌缩写 | 显示在页面 Logo 和登录页 |
| 平台标题 | 浏览器标签页标题 |
| 远程更新目录 | 升级包在目标服务器的存放路径 |
| 最大上传大小 | 升级包文件大小限制 |
| 允许上传的扩展名 | 逗号分隔，如 `.tar.gz,.zip` |

### 6.2 服务类型（系统设置 → 服务类型）

内置 `go` 和 `docker` 两种类型不可删除。管理员可以创建自定义服务类型（如 `java`、`python`），自定义升级步骤序列。

---

## 七、升级部署（平台自身更新）

当有新版本需要更新平台本身时：

```bash
# 1. 在开发机上构建前端
cd frontend && npm run build

# 2. 上传新代码到服务器
# 后端文件
tar czf - backend/app/ | ssh root@<server> 'cd /opt/deploy-platform && tar xzf -'
# 前端文件
tar czf - frontend/dist/ | ssh root@<server> 'cd /opt/deploy-platform && tar xzf -'

# 3. 更新 Python 依赖（如有新增）
ssh root@<server> '/opt/miniconda3/bin/conda run -n deploy-platform pip install -r /opt/deploy-platform/backend/requirements.txt'

# 4. 运行数据库迁移
ssh root@<server> 'cd /opt/deploy-platform/backend && /opt/miniconda3/bin/conda run -n deploy-platform alembic upgrade head'

# 5. 重启服务
ssh root@<server> 'systemctl restart deploy-platform'
```

---

## 八、文件路径总览

| 路径 | 说明 |
|------|------|
| `/opt/deploy-platform/backend/` | 后端代码 |
| `/opt/deploy-platform/backend/.env` | 环境变量 |
| `/opt/deploy-platform/backend/service_types.json` | 服务类型定义 |
| `/opt/deploy-platform/backend/platform_settings.json` | 平台运行时配置 |
| `/opt/deploy-platform/frontend/dist/` | 前端静态文件 |
| `/opt/deploy-platform/data/` | SQLite 数据库 |
| `/opt/deploy-platform/uploads/` | 升级包文件 |
| `/opt/deploy-platform/logs/` | 应用日志 |
| `/opt/miniconda3/envs/deploy-platform/` | Python 环境 |
| `/etc/systemd/system/deploy-platform.service` | systemd 服务定义 |

---

## 九、常用运维命令

```bash
# 查看服务状态
systemctl status deploy-platform

# 查看实时日志
journalctl -u deploy-platform -f

# 重启服务
systemctl restart deploy-platform

# 停止服务
systemctl stop deploy-platform

# 查看最近 50 行日志
journalctl -u deploy-platform -n 50 --no-pager
```

---

## 十、备份恢复

```bash
# 备份（数据库 + 上传文件）
tar czf cmi-backup-$(date +%Y%m%d).tar.gz \
  /opt/deploy-platform/data/ \
  /opt/deploy-platform/uploads/ \
  /opt/deploy-platform/backend/.env \
  /opt/deploy-platform/backend/service_types.json \
  /opt/deploy-platform/backend/platform_settings.json

# 恢复
tar xzf cmi-backup-YYYYMMDD.tar.gz -C /
systemctl restart deploy-platform
```

---

## 十一、故障排查

### 服务无法启动

```bash
# 查看详细错误
journalctl -u deploy-platform -n 50 --no-pager

# 手动启动测试
cd /opt/deploy-platform/backend
/opt/miniconda3/bin/conda run -n deploy-platform uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端页面 404

检查后端是否正确指向前端 dist 目录。`app/main.py` 中：
```python
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
```
确认 `/opt/deploy-platform/frontend/dist/index.html` 存在。

### 数据库锁定

SQLite 高并发下偶发锁定，重启即可：
```bash
systemctl restart deploy-platform
```

### Alembic 迁移失败

```bash
# 查看当前迁移版本
cd /opt/deploy-platform/backend
/opt/miniconda3/bin/conda run -n deploy-platform alembic current

# 查看迁移历史
/opt/miniconda3/bin/conda run -n deploy-platform alembic history
```

---

## 十二、安全建议

1. **修改 JWT 密钥**：务必设置 `APP_JWT_SECRET_KEY` 为随机字符串
2. **关闭 DEBUG**：生产环境设置 `APP_DEBUG=false`
3. **防火墙**：限制 8000 端口访问来源 IP
4. **HTTPS**：前置 Nginx 反向代理 + SSL 证书
5. **数据库**：高负载场景建议切换到 PostgreSQL
6. **定期备份**：建议每日备份 data/ 目录
