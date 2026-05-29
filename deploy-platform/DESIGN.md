# Deploy Platform — 运维升级发布平台 — 设计方案

> **项目概述**：Deploy Platform — 运维升级发布平台是一个自动化运维部署升级系统，用于替代手动运维升级流程，将手工升级步骤固化为自动化流程，支持 Go 二进制服务升级和 Docker 容器服务升级。
>
> **核心目标**：将原本需要手动 SSH 到多台机器逐服务执行的升级操作，简化为上传升级包 → 选择服务 → 一键执行 → 实时查看日志 → 完成或回退。

---

## 一、项目背景与定位

### 1.1 项目背景

运维基础设施通常包含告警管理、日志采集、Webhook 回调等多个子模块，部署在多套环境中。

传统升级操作依赖人工，运维人员需手动 SSH 到各节点逐服务执行命令。整套升级涉及多个服务，分布在多台服务器上，每次升级耗时较长。

### 1.2 运维文档分析

通过对现有 升级文档的分析，整个升级可归纳为两种操作模式：

**Go 二进制服务升级模式（网关+后端处理服务）**

1. 进入程序目录 `/opt/<service-name>`
2. 备份旧二进制文件（按日期命名）
3. 从 `/opt/update/<日期>/` 复制新二进制文件
4. 版本校验（`./binary -v`）+ MD5 校验
5. `sh run.sh stop` 停服 → 进程监控自动拉起 → `sh run.sh id` 确认
6. 日志检查（`grep 'start server success' logs/` 或 `tail -f logs/`）
7. 回退：还原备份文件 + `sh run.sh stop`

**Docker 容器服务升级模式（前端+Java 后端）**

1. UAT 环境 `docker save` 打包镜像
2. SCP 传输镜像包到目标节点 `/opt/update/<日期>/`
3. 目标节点 `docker load` 导入镜像
4. 修改 `run.sh` 脚本（注释 `docker rmi` 命令）
5. `sh run.sh <旧版本> <新版本>` 启动容器
6. `docker logs` 检查 + 页面功能验证
7. 回退：`sh run.sh <新版本> <旧版本>` 切回旧容器

### 1.3 平台定位

本平台本质上是一个 **「自动化运维执行器」**——将手工升级步骤固化为自动化流程，实现：

- 升级包统一管理（上传、校验、分发）
- 升级步骤自动编排（按依赖顺序，多节点并行）
- 实时日志查看（WebSocket 推送）
- 一键回退（保留备份）
- 操作审计（谁、什么时间、做了什么、结果如何）

---

## 二、总体架构

### 2.1 系统架构

平台采用**单体 B/S 架构**，一个 Python FastAPI 服务承载所有后端逻辑和前端静态资源，部署为单个 Docker 容器。通过 SSH/SCP 与远程目标服务器中的服务器交互。

架构层次：

- **前端层**：Vue 3 SPA，打包为静态文件，由 FastAPI 直接托管
- **API 网关层**：FastAPI REST API + WebSocket（实时日志）
- **业务逻辑层**：SSH 执行器、升级编排引擎、文件分发器、日志采集器
- **数据层**：SQLAlchemy ORM + SQLite（可切换 PostgreSQL）
- **目标环境**：通过 SSH 连接远程目标服务器

### 2.2 部署架构

| 组件 | 说明 |
|------|------|
| 连接方式 | SSH（paramiko）+ SCP 文件传输 |

### 2.3 服务类型

所有服务分为两种部署类型：

| 类型 | 部署方式 | 进程管理 | 示例服务 |
|------|---------|---------|---------|
| **Go 二进制** | 直接运行二进制文件，由进程监控守护 | `sh run.sh id/stop` | example-go-service 等 |
| **Docker 容器** | Docker 容器运行 | `sh run.sh <old> <new>` | example-web, example-api 等 |

---

## 三、技术栈选型

### 3.1 技术选型总览

| 层级 | 选型 | 选型理由 |
|------|------|---------|
| 后端框架 | **FastAPI** (Python 3.11+) | 异步高性能、自动生成 Swagger 文档、原生 WebSocket 支持、类型安全 (Pydantic) |
| ORM | **SQLAlchemy + Alembic** | Python 生态最成熟的 ORM，支持迁移管理 |
| 认证 | **JWT (python-jose) + bcrypt** | 无状态认证，无需 Redis/Session 存储 |
| SSH 远程执行 | **paramiko + scp** | Python 原生 SSH 库，无需在目标机安装 agent |
| 数据库 | **SQLite**（默认） | 零依赖、单体部署友好，可随时切换 PostgreSQL |
| 前端框架 | **Vue 3 + Element Plus** | 国内社区活跃，运维面板组件丰富，TypeScript 支持 |
| 前端构建 | **Vite** | 快速开发构建，HMR 热更新 |
| 状态管理 | **Pinia** | Vue 3 官方推荐，轻量 |
| HTTP 请求 | **Axios** | 前端 API 请求层 |
| 打包部署 | **Docker**（单容器） | 整体打包，前端静态文件由 FastAPI 直接托管 |

### 3.2 核心技术依赖

```
fastapi==0.115.*
uvicorn[standard]==0.34.*
sqlalchemy==2.0.*
alembic==1.14.*
paramiko==3.5.*
scp==0.15.*
python-jose[cryptography]==3.3.*
bcrypt==4.2.*
python-multipart==0.0.*
pydantic==2.10.*
pydantic-settings==2.7.*
aiofiles==24.1.*
```

---

## 四、数据库设计

### 4.1 核心表关系

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| **environments** | 环境定义 | id, name, description, ssh_default_port |
| **services** | 服务注册 | id, environment_id, name, type(go/docker), deploy_path, run_script, upgrade_order, depends_on |
| **service_nodes** | 服务部署节点 | id, service_id, host_ip, ssh_port, ssh_user, status |
| **upgrade_packages** | 升级包记录 | id, service_id, version, file_path, file_md5, file_size, created_at |
| **upgrade_tasks** | 升级任务 | id, environment_id, title, status, created_by, started_at, finished_at |
| **task_steps** | 任务步骤详情 | id, task_id, service_id, node_id, step_type, status, log_output, started_at, finished_at |
| **users** | 用户表 | id, username, password_hash, role, created_at |
| **audit_logs** | 操作审计 | id, user_id, action, target_type, target_id, detail, ip_address, created_at |

### 4.2 services 表详细设计

```sql
CREATE TABLE services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    environment_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,           -- 'go' | 'docker'
    deploy_path VARCHAR(255),            -- 部署目录路径，如 /opt/example-service
    run_script VARCHAR(50) DEFAULT 'run.sh',
    start_cmd VARCHAR(255),
    stop_cmd VARCHAR(255),
    check_cmd VARCHAR(255),
    version_cmd VARCHAR(255),
    backup_pattern VARCHAR(255),
    upgrade_order INTEGER DEFAULT 0,     -- 升级顺序
    depends_on VARCHAR(500),             -- 前置依赖服务ID，逗号分隔
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 task_steps 表设计

每个升级任务包含多个步骤，每个步骤对应一个服务在某个节点上的操作。

```sql
CREATE TABLE task_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    service_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    step_type VARCHAR(30),               -- backup|upload|verify|stop|start|check|rollback
    step_order INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending|running|success|failed|skipped
    log_output TEXT,
    error_message TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

---

## 五、核心功能模块

### 5.1 模块总览

| 模块 | 核心职责 | 关键技术点 |
|------|---------|-----------|
| **服务拓扑管理** | 管理服务定义、节点配置、升级顺序、依赖关系 | CRUD + SSH 连接测试 |
| **升级包管理** | 上传升级包、MD5 校验、版本列表、自动分发到目标节点 | 文件上传、SCP 分发、MD5 校验 |
| **升级执行引擎** | 按编排顺序执行升级、多节点并行、实时日志推送 | SSH 执行、WebSocket 推送、异步任务 |
| **状态巡检** | 批量检查所有服务运行状态（进程/容器/端口） | SSH 批量执行、结果汇总 |
| **回退管理** | 按备份信息一键回退到旧版本 | 备份文件还原、Docker 容器切换 |
| **环境管理** | 多环境配置、SSH 凭据管理 | 环境配置隔离 |
| **认证审计** | JWT 用户认证、操作日志记录、查询 | JWT + bcrypt + 审计中间件 |

### 5.2 SSH 执行器设计

SSH 执行器是平台的核心基础设施，封装 paramiko 库，提供：

- **连接池管理**：复用 SSH 连接，避免频繁建立/断开
- **命令执行**：支持超时控制、实时输出流式返回
- **文件传输**：基于 SCP 的文件上传/下载
- **连接测试**：验证 SSH 连通性和认证

```python
class SSHExecutor:
    async def execute(self, host: str, command: str, timeout: int = 30) -> SSHResult
    async def upload_file(self, host: str, local_path: str, remote_path: str) -> bool
    async def test_connection(self, host: str, port: int, user: str) -> bool
    async def execute_batch(self, hosts: list[str], command: str) -> list[SSHResult]
```

### 5.3 升级编排引擎设计

升级编排引擎负责按 运维文档定义的步骤顺序，编排整个升级流程：

- **步骤解析**：根据服务类型（go/docker）自动生成操作步骤序列
- **依赖排序**：按 upgrade_order 和 depends_on 字段决定执行顺序
- **并行执行**：同一服务多节点并行操作，不同服务按序串行
- **状态追踪**：实时更新每个步骤的状态（pending → running → success/failed）
- **失败处理**：步骤失败时可选择暂停等待人工介入或跳过继续

---

## 六、升级流程设计

### 6.1 完整升级流程

> **升级任务生命周期**：创建任务 → 上传升级包 → 分发到目标节点 → 按序执行升级步骤 → 健康检查 → 完成 / 回退

### 6.2 Go 二进制服务升级步骤

| 步骤 | 操作 | 命令示例 |
|------|------|---------|
| 1. 预检查 | 记录当前版本和进程 ID | `./binary -v && sh run.sh id` |
| 2. 备份 | 按日期备份当前二进制 | `cp binary binary.20260528` |
| 3. 上传 | SCP 分发新二进制文件 | `scp binary root@host:/opt/service/` |
| 4. 校验 | 版本号 + MD5 校验 | `./binary -v && md5sum binary` |
| 5. 停服 | 停止当前进程 | `sh run.sh stop` |
| 6. 确认拉起 | 等待进程监控自动拉起 | `sleep 3 && sh run.sh id` |
| 7. 日志检查 | 确认服务启动成功 | `grep "start server success" logs/` |

### 6.3 Docker 容器服务升级步骤

| 步骤 | 操作 | 命令示例 |
|------|------|---------|
| 1. 打包镜像 | 在 UAT 环境导出镜像 | `docker save -o image.tar.gz registry/image:tag` |
| 2. 分发镜像 | SCP 传输到目标节点 | `scp image.tar.gz root@host:/opt/update/` |
| 3. 导入镜像 | docker load 导入 | `docker load < image.tar.gz` |
| 4. 修改脚本 | 注释 docker rmi 防止误删 | `sed -i 's/docker rmi/#docker rmi/' run.sh` |
| 5. 启动容器 | 切换新版本容器 | `sh run.sh old-version new-version` |
| 6. 状态检查 | 容器运行状态 + 日志 | `docker ps && docker logs --tail 50` |

### 6.4 回退流程

> **回退触发条件**：新版本功能异常、业务受影响、操作超时、异常告警无法处理

**Go 服务回退**：还原备份文件 → `sh run.sh stop` → 等待自动拉起 → 确认旧版本进程

**Docker 服务回退**：`sh run.sh <新版本> <旧版本>` → 切回旧容器 → `docker logs` 确认

---

## 七、前端页面设计

### 7.1 页面路由规划

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录页 | `/login` | 用户登录，JWT 认证 |
| 仪表盘 | `/` | 环境选择器、服务状态总览卡片、最近升级记录、快速操作入口 |
| 服务管理 | `/services` | 服务列表（按环境/类型筛选）、节点配置、升级顺序配置、SSH 连通性测试 |
| 升级包管理 | `/packages` | 上传升级包、版本列表、MD5 信息、关联服务 |
| 新建升级 | `/upgrade/new` | 选择环境 → 选择服务（支持多选） → 上传/选择升级包 → 预览执行步骤 → 确认开始 |
| 升级详情 | `/upgrade/:id` | 实时步骤进度（WebSocket）、节点日志流式展示、步骤状态标记、一键回退按钮 |
| 升级历史 | `/upgrades` | 历史任务列表、按环境/时间/状态筛选、查看详情 |
| 状态巡检 | `/patrol` | 一键巡检、服务状态卡片（绿色正常/红色异常）、异常详情 |
| 操作审计 | `/audit` | 操作日志列表、按用户/操作类型/时间筛选 |
| 系统设置 | `/settings` | 环境配置（SSH 信息）、用户管理（管理员） |

### 7.2 仪表盘设计

仪表盘是登录后的首页，提供全局视图：

- **顶部环境选择器**：切换环境，全局生效
- **服务状态卡片**：按服务类型分组，展示 Go 服务 / Docker 服务的在线节点数/总节点数
- **最近升级记录**：最近的 5 条升级任务，含状态标签
- **快速操作按钮**：「新建升级」、「一键巡检」

### 7.3 升级执行页设计

这是平台最核心的页面，分三步向导：

1. **选择服务**：从服务列表中勾选本次要升级的服务（按 upgrade_order 排序展示）
2. **关联升级包**：上传或从已有包中选择，自动校验 MD5
3. **确认执行**：预览完整执行计划（服务 → 节点 → 步骤），点击「开始升级」

执行过程中，页面分为左右两栏：

- **左侧：步骤列表**，树形展示 服务 → 节点 → 步骤，每步有状态图标（等待/执行中/成功/失败）
- **右侧：实时日志**，选中某步骤后展示该步骤的 SSH 输出日志，通过 WebSocket 实时推送

---

## 八、项目目录结构

```
deploy-platform/
├── backend/
    │   ├── app/
    │   │   ├── main.py              # FastAPI 应用入口
    │   │   ├── config.py            # 配置管理（环境变量 + .env）
    │   │   ├── database.py          # 数据库连接和会话管理
    │   │   ├── models/              # SQLAlchemy 数据模型
    │   │   │   ├── __init__.py
    │   │   │   ├── environment.py
    │   │   │   ├── service.py
    │   │   │   ├── service_node.py
    │   │   │   ├── upgrade_package.py
    │   │   │   ├── upgrade_task.py
    │   │   │   ├── task_step.py
    │   │   │   ├── user.py
    │   │   │   └── audit_log.py
    │   │   ├── schemas/             # Pydantic 请求/响应模型
    │   │   │   ├── __init__.py
    │   │   │   ├── auth.py
    │   │   │   ├── service.py
    │   │   │   ├── upgrade.py
    │   │   │   └── patrol.py
    │   │   ├── api/                 # REST API 路由
    │   │   │   ├── __init__.py
    │   │   │   ├── auth.py          # /api/auth/*
    │   │   │   ├── services.py      # /api/services/*
    │   │   │   ├── packages.py      # /api/packages/*
    │   │   │   ├── upgrades.py      # /api/upgrades/*
    │   │   │   ├── patrol.py        # /api/patrol/*
    │   │   │   ├── environments.py  # /api/environments/*
    │   │   │   └── audit.py         # /api/audit/*
    │   │   ├── services/            # 业务逻辑层
    │   │   │   ├── __init__.py
    │   │   │   ├── ssh_executor.py        # SSH 连接 + 命令执行
    │   │   │   ├── upgrade_engine.py      # 升级编排引擎
    │   │   │   ├── go_service.py          # Go 服务升级逻辑
    │   │   │   ├── docker_service.py      # Docker 服务升级逻辑
    │   │   │   ├── package_manager.py     # 升级包管理
    │   │   │   └── patrol.py              # 状态巡检
    │   │   ├── auth/                # 认证模块
    │   │   │   ├── __init__.py
    │   │   │   ├── jwt_handler.py
    │   │   │   └── middleware.py
    │   │   └── utils/               # 工具函数
    │   │       ├── __init__.py
    │   │       └── logger.py
    │   ├── requirements.txt
    │   ├── alembic.ini
    │   ├── alembic/                 # 数据库迁移
    │   │   ├── env.py
    │   │   └── versions/
    │   └── Dockerfile
    ├── frontend/
    │   ├── src/
    │   │   ├── main.ts              # Vue 应用入口
    │   │   ├── App.vue              # 根组件
    │   │   ├── router/
    │   │   │   └── index.ts
    │   │   ├── stores/              # Pinia 状态管理
    │   │   │   ├── auth.ts
    │   │   │   ├── environment.ts
    │   │   │   └── upgrade.ts
    │   │   ├── api/                 # API 请求层
    │   │   │   ├── client.ts        # Axios 实例
    │   │   │   ├── auth.ts
    │   │   │   ├── services.ts
    │   │   │   ├── packages.ts
    │   │   │   ├── upgrades.ts
    │   │   │   └── patrol.ts
    │   │   ├── views/               # 页面组件
    │   │   │   ├── Login.vue
    │   │   │   ├── Dashboard.vue
    │   │   │   ├── ServiceList.vue
    │   │   │   ├── PackageList.vue
    │   │   │   ├── UpgradeNew.vue
    │   │   │   ├── UpgradeDetail.vue
    │   │   │   ├── UpgradeHistory.vue
    │   │   │   ├── Patrol.vue
    │   │   │   ├── AuditLog.vue
    │   │   │   └── Settings.vue
    │   │   ├── components/          # 通用组件
    │   │   │   ├── EnvSelector.vue
    │   │   │   ├── ServiceCard.vue
    │   │   │   ├── StepTree.vue
    │   │   │   └── LogViewer.vue
    │   │   └── assets/
    │   ├── package.json
    │   ├── vite.config.ts
    │   ├── tsconfig.json
    │   └── index.html
    ├── docker-compose.yml
    ├── DESIGN.md
    └── README.md
```

---

## 九、实施路径

### 9.1 分阶段实施计划

| 阶段 | 名称 | 核心内容 | 预估工时 |
|------|------|---------|---------|
| Phase 1 | **基础框架搭建** | 项目骨架（FastAPI + Vue 3）、数据库模型创建、Alembic 迁移、JWT 认证、前端路由框架 | 3-5 天 |
| Phase 2 | **服务与环境管理** | 服务 CRUD、节点配置、SSH 连接测试、环境配置管理、前端服务管理页面 | 3-5 天 |
| Phase 3 | **升级包管理** | 文件上传 API、MD5 校验、SCP 文件分发、升级包版本列表、前端升级包页面 | 2-3 天 |
| Phase 4 | **升级执行引擎** | SSH 执行器、Go 服务升级流程、Docker 服务升级流程、WebSocket 实时日志推送、升级执行页面 | 5-7 天 |
| Phase 5 | **任务编排与回退** | 多服务依赖排序、多节点并行执行、回退逻辑、失败处理策略、升级详情页面 | 3-5 天 |
| Phase 6 | **状态巡检与仪表盘** | 批量状态检查、仪表盘页面、巡检页面 | 2-3 天 |
| Phase 7 | **收尾完善** | 操作审计日志、用户管理、Docker 化部署、文档完善、边界测试 | 2-3 天 |

> **总预估工时**：20-30 个工作日（约 1-1.5 个月），建议 Phase 1-3 完成后即可进行内部试用，Phase 4-5 为核心功能重点投入，Phase 6-7 为完善和收尾。

### 9.2 技术风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| SSH 连接不稳定 | 升级中断、状态不一致 | 增加重试机制、超时控制、断线重连 |
| 升级步骤执行失败 | 服务不可用、业务中断 | 每步前置校验、失败自动暂停、支持手动介入 |
| 多环境配置差异 | 不同环境执行结果不同 | 每环境独立配置、升级前 dry-run 校验 |
| 并发文件分发性能 | 大文件传输慢 | 分片传输、进度展示、失败重传 |
