<h1 align="center">📈 GitHub Daily Trending</h1>

<p align="center">
  <b>每日从 GitHub Trending 页面爬取热门开源项目 Top 10</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg">
  <img src="https://img.shields.io/badge/dependencies-zero-brightgreen">
  <img src="https://img.shields.io/badge/license-MIT-green">
</p>

---

## ✨ 特性

- **📊 每日 Top 10** — 从 GitHub Trending 页面抓取当日热门项目（全语言总榜）
- **🔍 精准筛选** — 自动过滤非仓库条目（sponsors、login 等）
- **📋 详情完整** — 包含排名、Star 总数、日/周/月增长量、开源时间、项目描述
- **🌏 中文翻译** — 自动将英文描述翻译为中文（基于 Google Translate 免费接口）
- **🔌 零依赖** — 纯 Python 3.8+ 标准库，无需安装任何第三方包
- **🎯 GitHub API** — 调用 GitHub API 获取准确的 star 数量、创建时间等细节
- **📤 多格式输出** — 支持 Telegram 消息格式、Markdown 和 JSON
- **💾 自动存档** — 数据按 `YYYY/YYYYMMDD.md` 结构保存，并自动 git commit & push
- **⏰ 定时执行** — 配合 Cron/定时任务，每日自动运行
- **🔑 Token 支持** — 可选配置 GH_TOKEN 避免 API 限流

## 🎯 输出预览

```
📅 GitHub 热门开源项目 | 2026.05.19

🏆 日榜最佳项目: [owner/repo](https://github.com/owner/repo)
   ⭐️ 总星标数量：78.7k
   🔺 日增长数量：3029⭐
   📝 项目描述（中文翻译）

━━━ 📊 日榜排行 ━━━

| 排名 | 项目名 | Star⭐ | 今日增长量 |
|------|--------|--------|-----------|
| 1    | [owner/repo] | 78.7k | 🔺3029 |
| 2    | [owner/repo] | 5.0k  | 🔺2531 |
...

━━━ 📋 日榜项目详情 ━━━

*#1.* [owner/repo](https://github.com/owner/repo)
   ⭐️ 总星标数量：78.7k
   🔺 日增长数量：3029⭐
   🔺 上周增长数量：14052⭐
   🔺 上月增长数量：63682⭐
   📅 开源时间：2026-02-03
   📝 项目描述：项目描述中文翻译
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 网络连接（需访问 github.com、api.github.com 和 translate.googleapis.com）

### 使用

```bash
# 1. 下载脚本
curl -O https://raw.githubusercontent.com/Yangsiyu0117/WorkScript/main/github-trending/github_trending.py

# 2. 运行（获取今日数据）
python github_trending.py

# 3. Markdown 格式输出（带 GitHub API 详情）
python github_trending.py --output md

# 4. JSON 格式输出
python github_trending.py --output json

# 5. 指定日期（用于回看历史数据）
python github_trending.py --date 20260519
```

### 使用 GitHub Token（推荐）

配置 `GH_TOKEN` 环境变量可以大幅提高 API 调用频率限制：

```bash
export GH_TOKEN="github_pat_xxxxxxxx"
python github_trending.py
```

## 📖 完整参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--date` | 指定日期（YYYYMMDD格式） | 当天日期 |
| `--output` | 输出格式：`tg`（Telegram）、`md`（Markdown）、`json` | `tg` |
| `--no-save` | 不保存到本地存档 | false（自动保存） |
| `--no-push` | 不推送到远程仓库 | false（自动推送） |
| `--token` | GitHub Token（优先级高于环境变量 GH_TOKEN） | `$GH_TOKEN` 或无 |
| `-h, --help` | 显示帮助信息 | - |

### 输出格式说明

- **`tg` 模式**：输出美化后的 Markdown 消息，适合 Telegram / Discord / Slack 直接发送
- **`md` 模式**：完整 Markdown 文档格式，包含详细项目描述
- **`json` 模式**：结构化 JSON 数据，适合程序处理或二次开发

## 🔧 集成示例

### 定时任务（Linux Cron）

```bash
# 每天早上 8:30 运行
30 8 * * * cd /path/to/script && python github_trending.py --output md

# 带 Token 运行
30 8 * * * export GH_TOKEN="github_pat_xxx" && cd /path/to/script && python github_trending.py
```

### 脚本中调用

```python
import subprocess
import json

result = subprocess.run(
    ["python", "github_trending.py", "--output", "json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
for repo in data["top_10"]:
    print(f"#{repo['rank']} {repo['full_name']} ⭐{repo['stars_display']}")
```

### Webhook 推送

```bash
# 获取 JSON 数据
DATA=$(python github_trending.py --output json --no-save)

# 推送到自建 Server
curl -X POST https://your-server.com/webhook \
  -H "Content-Type: application/json" \
  -d "$DATA"
```

## 📚 数据来源

| 来源 | 说明 |
|------|------|
| **GitHub Trending** | [github.com/trending](https://github.com/trending) — 每日热门项目原始排行榜 |
| **GitHub API** | [api.github.com](https://api.github.com) — 获取仓库详细数据（Star 数、创建时间等） |

## 📁 项目结构

```
github-trending/
├── github_trending.py    # 主脚本（零依赖，直接从 GitHub Trending 爬取）
├── README.md             # 本文件
├── LICENSE               # MIT 许可证
├── .gitignore            # Git 忽略规则
└── data/
    └── YYYY/             # 数据存档（按年/日组织）
        └── YYYYMMDD.md
```

## ⚠️ 注意事项

1. **API 限流**：未配置 Token 时，GitHub API 每小时最多 60 次请求。配置 GH_TOKEN 后提升至 5000 次/小时
2. **翻译限流**：Google Translate 免费接口有隐性限流，脚本默认在每次翻译之间添加延迟
3. **网络要求**：需能访问 `github.com`、`api.github.com` 和 `translate.googleapis.com`
4. **数据时效**：Trending 页面实时更新，凌晨数据可能较少，建议上午 8-10 点运行
5. **中文翻译**：翻译结果仅供参考，部分技术术语可能保留原文更合适

## 🤝 贡献

欢迎提交 Issue 和 PR！如果你有好的想法或改进建议，请随时贡献。

## 📄 许可证

[MIT License](LICENSE) © 2026 Yangsiyu
