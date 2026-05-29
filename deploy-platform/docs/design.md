# Deploy Platform — 运维升级发布平台 — 设计方案

> **版本**: v0.5.1 | **最后更新**: 2026-05-29

---

## 一、项目概述

### 1.1 背景

该项目包含多个服务，部署在多环境的服务器上。升级操作长期依赖手动文档，运维人员需逐台 SSH 执行命令，单次升级耗时长，容易出错且无法追溯。

### 1.2 目标

将手动升级流程固化为 Web 平台自动化执行，实现：

- 升级包统一上传、校验、分发
- 升级步骤按依赖顺序自动编排，多节点并行
- 实时日志 WebSocket 推送
- 一键回退（保留备份文件）
- 全操作审计追溯

### 1.3 服务类型

通过对现有运维文档归纳，所有服务分为两类：

| 类型 | 部署方式 | 进程管理 |
|------|---------|---------|
| Go 二进制 | 直接运行 binary，由进程监控守护 | `sh run.sh id/stop` |
| Docker 容器 | 容器化运行 | `sh run.sh <old> <new>` 切换容器 |

---

## 二、技术架构

### 2.1 总体架构

```
┌──────────────────────────────────────────────────┐
│                    浏览器 (SPA)                     │
│           Vue 3 + Element Plus + Pinia             │
└────────────────────┬─────────────────────────────┘
                     │ HTTP / WebSocket
┌────────────────────┴─────────────────────────────┐
│              FastAPI Server (:8000)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ REST API │ │ WebSocket│ │ Static Files     │  │
│  │ (CRUD)   │ │ (日志流) │ │ (前端 SPA)        │  │
│  └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────────────────────────────────────────┐ │
│  │           业务逻辑层                           │ │
│  │  SSH执行器 │ 升级引擎 │ 包管理器 │ 巡检服务    │ │
│  └──────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────┐ │
│  │              SQLAlchemy ORM                    │ │
│  └──────────────────┬───────────────────────────┘ │
└─────────────────────┼─────────────────────────────┘
                      │
              ┌───────┴───────┐
              │   SQLite DB    │
              └───────────────┘
                      │ SSH / SFTP (Paramiko)
     ┌────────────────┼────────────────┐
     ▼                ▼                ▼
┌─────────┐    ┌─────────┐     ┌─────────┐
│ Production 环境 │    │ Staging 环境 │     │   ...    │
│ 10+ 服务器│   │ 10+ 服务器│    │         │
└─────────┘    └─────────┘     └─────────┘
```

### 2.2 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI (Python 3.11) | 0.115.x |
| ASGI 服务器 | Uvicorn | 0.34.x |
| ORM | SQLAlchemy 2.0 + Alembic | 2.0.x / 1.14.x |
| 数据库 | SQLite（默认，可切换 PostgreSQL） | — |
| 认证 | JWT (python-jose) + bcrypt (passlib) | — |
| SSH | Paramiko + SCP | 3.5.x |
| 加密 | AES-256-GCM (cryptography) | — |
| 前端框架 | Vue 3 + TypeScript | 3.x |
| UI 库 | Element Plus | 2.14.x |
| 状态管理 | Pinia | 3.0.x |
| 构建 | Vite | 8.x |

### 2.3 关键设计决策

**为什么选 SQLite？**
单体部署场景下零依赖、免运维。通过 WAL 模式 + busy_timeout=5000ms 解决并发写入问题。生产环境可通过改 `APP_DATABASE_URL` 一键切换到 PostgreSQL。

**为什么用 Paramiko 而不是 Ansible？**
平台定位是自动化运维执行器而非通用配置管理工具。Paramiko 提供精细的 SSH 控制，无需在目标机安装 agent，适合"上传 → 备份 → 替换 → 验证"这种固定流程。

**为什么前端由 FastAPI 直接托管？**
简化部署拓扑，一个进程承载全部功能，消除跨域问题和 Nginx 依赖。生产环境可在前面加 Nginx 反向代理。

---

## 三、数据库设计

### 3.1 ER 图（8 张表）

```
users ──┬── audit_logs (user_id SET NULL on delete)
        └── upgrade_tasks (created_by SET NULL on delete)

environments ──┬── services (cascade delete)
               └── upgrade_tasks

services ──┬── service_nodes (cascade delete)
           ├── upgrade_packages
           └── task_steps

upgrade_tasks ── task_steps (cascade delete)
```

### 3.2 表结构

#### environments（环境）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | VARCHAR(50) UNIQUE | 环境名称 |
| description | TEXT | 描述 |
| ssh_default_port | INTEGER | 默认 SSH 端口，默认 22 |

#### services（服务定义）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| environment_id | FK → environments | 所属环境 |
| name | VARCHAR(100) | 服务名称 |
| type | VARCHAR(20) | 服务类型（go/docker/自定义） |
| deploy_path | VARCHAR(255) | 部署目录 |
| run_script | VARCHAR(50) | 运行脚本名，默认 run.sh |
| start_cmd | VARCHAR(255) | 自定义启动命令 |
| stop_cmd | VARCHAR(255) | 自定义停止命令 |
| check_cmd | VARCHAR(255) | 自定义检查命令 |
| upgrade_order | INTEGER | 升级排序，越小越先 |
| depends_on | VARCHAR(500) | 前置依赖服务名，逗号分隔 |
| description | TEXT | 描述 |

#### service_nodes（服务节点）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| service_id | FK → services | 所属服务 |
| host_ip | VARCHAR(50) | 主机 IP |
| ssh_port | INTEGER | SSH 端口，默认 22 |
| ssh_user | VARCHAR(50) | SSH 用户，默认 root |
| ssh_password | VARCHAR(255) | AES-256-GCM 加密存储 |
| status | VARCHAR(20) | 节点状态 |

#### upgrade_packages（升级包）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| service_id | FK → services | 关联服务 |
| version | VARCHAR(50) | 版本号 |
| file_path | VARCHAR(500) | 本地存储路径 |
| file_md5 | VARCHAR(64) | MD5 校验值 |
| file_size | INTEGER | 文件大小(字节) |

唯一约束：(service_id, version)

#### upgrade_tasks（升级任务）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| environment_id | FK → environments | 目标环境 |
| title | VARCHAR(200) | 任务标题 |
| status | VARCHAR(30) | pending/running/paused/success/failed |
| failure_strategy | VARCHAR(20) | 失败策略：stop/continue/rollback |
| rollback_status | VARCHAR(20) | 回退状态 |
| is_rollback | BOOLEAN | 是否为回退任务 |
| timeout_seconds | INTEGER | 每步超时秒数 |
| created_by | FK → users | SET NULL on delete |

#### task_steps（任务步骤）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| task_id | FK → upgrade_tasks | 所属任务 |
| service_id | FK → services | 目标服务 |
| node_id | FK → service_nodes | 目标节点 |
| step_type | VARCHAR(30) | 步骤类型 key |
| step_order | INTEGER | 执行顺序 |
| status | VARCHAR(20) | pending/running/success/failed/skipped |
| rollback_status | VARCHAR(20) | 回退状态 |
| log_output | TEXT | SSH 命令输出 |
| error_message | TEXT | 错误信息 |
| retry_count | INTEGER | 重试次数 |

#### users（用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| username | VARCHAR(50) UNIQUE | 用户名 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| role | VARCHAR(20) | admin/operator |

#### audit_logs（审计日志）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| user_id | FK → users | SET NULL on delete |
| action | VARCHAR(50) | 操作类型 |
| target_type | VARCHAR(50) | 目标类型 |
| target_id | INTEGER | 目标 ID |
| detail | TEXT | 详细信息 |
| ip_address | VARCHAR(50) | 操作 IP |

---

## 四、API 设计

### 4.1 路由分组

| 前缀 | 模块 | 端点数 | 权限 |
|------|------|--------|------|
| `/api/auth` | 认证 | 2 | 公开（注册首次为 admin） |
| `/api/config` | 平台配置 | 4 | 读取公开，写入 admin |
| `/api/environments` | 环境管理 | 6 | 读取需登录，写入需 admin |
| `/api/services` | 服务管理 | 15 | 读取需登录，写入需 admin |
| `/api/packages` | 升级包 | 4 | 需登录 |
| `/api/upgrades` | 升级任务 | 10 + WS | 需登录 |
| `/api/patrol` | 巡检 | 1 | 需登录 |
| `/api/users` | 用户管理 | 4 | admin |
| `/api/audit` | 审计日志 | 1 | 需登录 |
| `/health` | 健康检查 | 1 | 公开 |

### 4.2 服务类型系统

服务类型定义在 `service_types.json` 中，内置两种：

**go 类型**：precheck → backup → upload → copy → verify → verify_version → stop → check_start → log_check
可回退：backup, upload, copy

**docker 类型**：docker_scp → docker_load → docker_verify → precheck → switch_container → container_check
可回退：docker_scp, switch_container

v0.5.1 起支持通过 API 创建自定义服务类型，前端设置页面可直接管理。

### 4.3 认证授权模型

- **JWT Token**: HS256 签名，480 分钟过期
- **角色**: admin（全部权限）、operator（读 + 升级操作）
- **自注册**: 首个用户自动成为 admin，后续注册默认 operator
- **密码存储**: bcrypt 哈希
- **SSH 密码**: AES-256-GCM 加密存储，密钥由 JWT secret 派生

### 4.4 平台配置优先级

`platform_settings.json` > `config.py` 默认值 > `.env` 环境变量

前端页面可直接修改平台设置（品牌、标题、上传限制等），保存后立即生效。

---

## 五、升级引擎设计

### 5.1 执行模型

```
创建任务 → 生成步骤（按 service_type 步骤序列展开）→ 分组排序 → 波浪式执行
```

**波浪式执行**：同一服务的所有节点在同一个 step_type 上并行执行，完成后进入下一个 step_type。服务间按 `upgrade_order` 和 `depends_on` 拓扑排序。

### 5.2 步骤生成规则

1. 按 `upgrade_order` 升序排列服务
2. 检查 `depends_on` 依赖（仅限同环境的其他服务名）
3. 每个服务的每个节点 × 该服务类型的每个步骤 = 一组 task_step 记录
4. 步骤按 (service_order, step_index) 排序

### 5.3 失败处理策略

| 策略 | 行为 |
|------|------|
| **stop** | 当前步骤失败后停止整个任务，等待人工介入 |
| **continue** | 记录失败，继续执行后续步骤 |
| **rollback** | 失败立即触发回退，按逆序执行可回退步骤 |

### 5.4 回退机制

- 仅回退标记为 rollbackable 的步骤类型
- 按执行逆序回退（后执行的先回退）
- Go 服务: 还原备份文件 → 重启
- Docker 服务: `sh run.sh <new> <old>` 切回旧容器
- 回退状态独立追踪（`rollback_status` 字段）

### 5.5 实时日志

- 每步执行时建立 SSH 连接，输出通过 asyncio 队列收集
- 前端通过 WebSocket 订阅任务日志流（`ws://host/api/upgrades/ws/{task_id}?token=xxx`）
- 日志同时持久化到 `task_steps.log_output`

### 5.6 孤儿任务恢复

服务启动时（lifespan handler），检测所有 `running`/`paused` 状态的升级任务，标记为 `failed`。防止服务器重启导致任务卡死。

---

## 六、前端设计

### 6.1 路由结构

| 路由 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | JWT 认证，首次注册 |
| `/` | 仪表盘 | 统计卡片、最近任务、快速入口 |
| `/services` | 服务管理 | 按环境筛选，服务/节点 CRUD |
| `/packages` | 升级包 | 上传、版本列表、MD5 |
| `/upgrade/new` | 新建升级 | 三步向导：选服务 → 选包 → 确认 |
| `/upgrade/:id` | 升级详情 | 步骤树 + 日志查看器（WebSocket） |
| `/upgrades` | 升级历史 | 任务列表，按状态筛选 |
| `/patrol` | 状态巡检 | 一键批量 SSH 检查 |
| `/audit` | 审计日志 | 操作记录查询 |
| `/settings` | 系统设置 | 四个 Tab：环境、用户、服务类型、平台设置 |

### 6.2 核心组件

- **EnvSelector**: 环境切换下拉框，全局生效
- **StepTree**: 树形展示 服务 → 节点 → 步骤，状态图标 + 操作按钮
- **LogViewer**: 终端风格日志查看器，搜索、级别筛选、自动滚动
- **ServiceCard**: 服务健康状态摘要卡片

### 6.3 状态管理 (Pinia)

**auth store**: token/username/role → localStorage 持久化
**environment store**: 当前选中环境，环境列表缓存

### 6.4 路由守卫

`router.beforeEach` 检查 `localStorage.getItem('token')`，未登录跳转 `/login`。

---

## 七、安全设计

| 层面 | 措施 |
|------|------|
| 传输安全 | 建议前置 Nginx + HTTPS |
| 认证 | JWT + bcrypt，8 小时过期 |
| 授权 | RBAC（admin/operator），API 级别校验 |
| SSH 密码 | AES-256-GCM 加密存储，密钥散列自 JWT secret |
| 登录保护 | 5 分钟内最多 5 次失败尝试（per IP） |
| 审计 | 自动记录所有关键操作（创建/修改/删除/执行） |
| SQL 注入 | ORM 参数化查询 |
| XSS | Vue 3 默认转义 + CSP 头 |
| CSRF | JWT Bearer token（非 Cookie） |

---

## 八、部署架构

### 8.1 推荐方式：Miniconda + systemd

```
/opt/deploy-platform/
├── backend/           # FastAPI 代码
│   ├── app/
│   ├── .env           # 环境变量
│   └── requirements.txt
├── frontend/
│   └── dist/          # SPA 构建产物
├── data/              # SQLite 数据库
└── uploads/           # 升级包存储
```

systemd 管理进程，journald 收集日志。

### 8.2 备选方式：Docker Compose

多阶段 Dockerfile 构建，三个持久卷（data/uploads/logs），生产就绪。

### 8.3 关键文件路径

| 路径 | 用途 |
|------|------|
| `backend/service_types.json` | 服务类型步骤定义 |
| `backend/platform_settings.json` | 运行时平台配置（API 可写） |
| `backend/.env` | 环境变量 |
| `data/deploy_platform.db` | SQLite 数据库 |
| `uploads/` | 升级包文件 |
| `logs/app.log` | 应用日志 |
| `logs/error.log` | 错误日志 |
| `logs/access.log` | HTTP 访问日志 |
