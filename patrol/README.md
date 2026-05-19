# Patrol 运维巡检平台

> 一个基于 Prometheus 的智能运维巡检系统，支持自动化巡检、多维度告警和实时报告通知。

## 功能特性

- **智能巡检引擎** — 自动化执行巡检任务，支持手动触发和定时调度
- **多数据源** — 支持 Prometheus 及多个数据源，灵活配置
- **丰富插件** — 内置多种巡检插件（Node Exporter、MySQL、Redis、Elasticsearch、Etcd、MinIO、Pulsar、cAdvisor、APISIX 等）
- **插件化架构** — 可轻松扩展自定义巡检插件
- **多通知渠道** — 支持飞书、邮件等多种通知方式，并可自定义报告格式
- **Web 管理界面** — 基于 React + Vite 构建的现代化管理界面
- **定时调度** — 基于 APScheduler 的 Cron 表达式调度
- **数据分析** — 巡检结果统计分析和趋势展示

## 系统架构

```
┌──────────────────────────────────────────────────┐
│                    Web UI                        │
│              (React + Tailwind)                  │
└──────────────────────┬───────────────────────────┘
                       │ HTTP API
┌──────────────────────┴───────────────────────────┐
│                 Flask Backend                    │
│     ┌─────────────┴─────────────┐                │
│     │       调度器/引擎         │                │
│     └──────┬──────────┬────────┘                │
│            │          │                          │
│     ┌──────┴──┐  ┌────┴──────┐                  │
│     │ 插件系统 │  │ 通知系统  │                  │
│     └──────┬──┘  └────┬──────┘                  │
│            │          │                          │
│     ┌──────┴──┐  ┌────┴──────┐                  │
│     │ Prometheus│ │ 飞书/邮件 │                  │
│     └─────────┘  └───────────┘                  │
└──────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求
- Python 3.8+
- Node.js 18+（构建前端）
- Prometheus 实例（可被网络访问）

### 安装部署

```bash
# 克隆仓库
git clone https://github.com/Yangsiyu0117/AI-Coding.git
cd AI-Coding

# 安装后端依赖
pip install -r requirements.txt

# 构建前端
cd web
npm install
npm run build
cd ..

# 初始化数据库
python3 -c "import app; app.init_db()"

# 启动服务
python3 app.py
```

访问 `http://localhost:5000` 进入管理界面。

### 一键安装

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

## 配置说明

编辑 `config.yaml` 配置文件：

```yaml
# 数据库路径
db_path: patrol.db

# 定时调度器
scheduler:
  enabled: true

# 默认项目配置
projects:
  - name: default
    env: production
    prometheus_url: http://localhost:9090
```

## 巡检插件

| 插件 | 说明 | 监控指标 |
|------|------|---------|
| `node_exporter` | 服务器基础监控 | CPU/内存/磁盘/网络 |
| `mysqld_exporter` | MySQL 数据库 | 连接数/慢查询/QPS |
| `redis_exporter` | Redis 缓存 | 内存/命中率/连接数 |
| `elasticsearch` | ES 集群 | 集群健康/节点状态 |
| `cadvisor` | 容器监控 | CPU/内存/网络 I/O |
| `pulsar` | Pulsar 消息队列 | 消息积压/消费速率 |
| `etcd` | etcd 集群 | Leader/事务/存储 |
| `minio` | MinIO 存储 | 存储量/请求速率 |
| `apisix` | APISIX 网关 | 路由/上游健康 |
| `process_exporter` | 进程监控 | 进程状态/资源 |
| `generic` | 通用 PromQL | 自定义指标查询 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/projects` | 项目列表 |
| `POST` | `/api/projects` | 创建项目 |
| `POST` | `/api/projects/{id}/inspect` | 触发巡检 |
| `GET` | `/api/records/{id}/report` | 获取巡检报告 |
| `POST` | `/api/records/{id}/send` | 发送报告到通知渠道 |
| `GET` | `/api/stats/overview` | 统计概览 |

完整 API 文档请查看 Web UI 界面。

## 通知渠道配置

### 飞书
```json
{
  "channel_type": "feishu",
  "config": {
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  }
}
```

### 邮件
```json
{
  "channel_type": "email",
  "config": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 465,
    "username": "user@example.com",
    "password": "xxx",
    "to": "ops@example.com"
  }
}
```

## 数据清理与维护

系统默认保留 90 天的巡检记录和通知日志，可在系统设置中调整保留天数。系统每天自动执行数据清理任务。

## 许可协议

[MIT License](LICENSE)