# Deploy Platform — 运维升级发布平台

基于角色的生产环境升级发布管理系统，支持 Go/Docker 服务的批量升级、状态巡检与操作审计。

## 技术栈

- **后端**: Python 3.11 + FastAPI + SQLAlchemy 2.0 + SQLite + JWT
- **前端**: Vue 3 + TypeScript + Vite + Element Plus + Pinia
- **远程执行**: Paramiko (SSH/SFTP)
- **部署**: Docker + docker-compose

## 功能模块

| 模块 | 说明 |
|------|------|
| 环境管理 | 多环境配置（开发/测试/生产），SSH 连接测试 |
| 服务管理 | 服务类型（Go/Docker）、节点配置、依赖关系、升级顺序 |
| 升级包管理 | 上传升级包、版本管理、MD5 校验 |
| 升级任务 | 拓扑排序、波浪式并行执行、失败策略（停止/继续/回滚） |
| 实时日志 | WebSocket 推送每步执行日志 |
| 状态巡检 | 一键批量 SSH 巡检所有服务节点 |
| 仪表盘 | 全局统计卡片、最近升级记录、快速操作入口 |
| 操作审计 | 自动记录所有关键操作，支持按类型筛选 |
| 用户管理 | 管理员/操作员角色、用户 CRUD |

## 项目结构

```
deploy-platform/
├── backend/
│   ├── app/
│   │   ├── api/           # REST API 路由
│   │   ├── auth/          # JWT 认证与权限中间件
│   │   ├── models/        # SQLAlchemy 数据模型
│   │   ├── schemas/       # Pydantic 请求/响应模型
│   │   ├── services/      # 业务逻辑（升级引擎、巡检、SSH）
│   │   └── utils/         # 日志配置
│   ├── alembic/           # 数据库迁移
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/           # 后端 API 调用封装
│   │   ├── components/    # 可复用组件
│   │   ├── stores/        # Pinia 状态管理
│   │   ├── views/         # 页面组件
│   │   └── router/        # 路由配置
│   └── package.json
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 快速开始（开发）

### 前置条件

- Python 3.11+
- Node.js 18+
- npm 9+

### 后端

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

首次启动后，访问 http://localhost:8000/docs 查看 Swagger API 文档。

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器默认运行在 http://localhost:5173，API 请求自动代理到后端。

### 默认账户

系统采用自助注册机制：**第一个注册的用户自动成为管理员**，后续注册用户默认为操作员。管理员可在「系统设置 → 用户管理」中管理其他用户。

## Docker 部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

服务运行在 `http://localhost:8000`。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_JWT_SECRET_KEY` | JWT 签名密钥（生产环境务必修改） | 内置默认值 |
| `APP_DATABASE_URL` | 数据库连接字符串 | `sqlite:///./deploy_platform.db` |
| `APP_UPLOAD_DIR` | 升级包上传目录 | `./uploads` |
| `APP_SSH_DEFAULT_TIMEOUT` | SSH 连接超时（秒） | `10` |

## API 概览

| 前缀 | 说明 | 权限 |
|------|------|------|
| `/api/auth` | 登录/注册 | 公开 |
| `/api/environments` | 环境 CRUD | 读取需登录，写入需 admin |
| `/api/services` | 服务与节点 CRUD | 同上 |
| `/api/packages` | 升级包上传/删除 | 登录用户 |
| `/api/upgrades` | 升级任务与 WebSocket | 登录用户 |
| `/api/patrol` | 状态巡检 | 登录用户 |
| `/api/users` | 用户管理 | admin |
| `/api/audit` | 操作审计日志 | 登录用户 |
| `/health` | 健康检查 | 公开 |
