<h1 align="center">📈 GitHub Daily Trending</h1>

<p align="center">
  <b>每日自动获取 GitHub 热门开源项目 Top 10，自动翻译项目描述为中文</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg">
  <img src="https://img.shields.io/badge/dependencies-zero-brightgreen">
  <img src="https://img.shields.io/badge/license-MIT-green">
  <img src="https://img.shields.io/badge/no%20token-required-success">
</p>

---

## ✨ 特性

- **📊 每日 Top 10** — 获取 GitHub 全语言热门项目排行榜（按日/周/月增长排序）
- **📋 详情完整** — 包含排名、Star 总数、日/周/月增长量、开源时间、项目描述
- **🌏 中文翻译** — 自动将英文描述翻译为中文（基于 Google Translate 免费接口）
- **🔌 零依赖** — 纯 Python 3.8+ 标准库，无需安装任何第三方包
- **🔑 无需 Token** — 直接从原始数据文件读取，无需 GitHub API Token
- **📤 多格式输出** — 支持 Telegram 消息格式和 JSON 格式
- **🤖 可集成** — 可用于 Cron 定时任务、Telegram Bot、CI/CD 流程等

## 🎯 输出预览

```
📅 GitHub 热门开源项目 | 2026.05.18

🏆 日榜最佳项目: [mattpocock/skills](https://github.com/mattpocock/skills)
   ⭐ 总星标数量：78.7k
   🔺 日增长数量：3029⭐
   📝 我的个人技能目录，直接来自我的 .claude 目录。

━━━ 📊 日榜排行 ━━━

| 排名 | 项目名                      | Star⭐  | 今日增长量 |
|------|-----------------------------|--------|-----------|
| 1    | [mattpocock/skills]         | 78.7k  | 🔺3029    |
| 2    | [tinyhumansai/openhuman]    | 5.0k   | 🔺2531    |
| 3    | [CloakHQ/CloakBrowser]      | 9.3k   | 🔺1753    |
| ...  |                             |        |           |

━━━ 📋 日榜项目详情 ━━━

*#1.* [mattpocock/skills](https://github.com/mattpocock/skills)
   ⭐ 总星标数量：78.7k
   🔺 日增长数量：3029⭐
   🔺 上周增长数量：14052⭐
   🔺 上月增长数量：63682⭐
   📅 开源时间：2026-02-03
   📝 项目描述：我的个人技能目录，直接来自我的 .claude 目录。
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 网络连接（需访问 raw.githubusercontent.com 和 translate.googleapis.com）

### 使用

```bash
# 1. 下载脚本
curl -O https://raw.githubusercontent.com/Yangsiyu0117/WorkScript/main/github-trending/github_trending.py

# 2. 运行（自动获取最新日期的数据）
python github_trending.py

# 3. 指定日期
python github_trending.py --date 20260518

# 4. JSON 格式输出
python github_trending.py --output json

# 5. 跳过中文翻译（保留英文描述）
python github_trending.py --no-translate
```

## 📖 完整参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--date` | 指定日期（YYYYMMDD格式） | 自动获取最新可用数据 |
| `--output` | 输出格式：`tg`（Telegram 格式）或 `json` | `tg` |
| `--no-translate` | 跳过中文翻译，保留原文 | false（开启翻译） |
| `-h, --help` | 显示帮助信息 | - |

### 输出格式说明

- **`tg` 模式**：输出美化后的 Markdown 消息，包含最佳项目突出、排行榜表格、项目详情三个部分，适合 Telegram / Discord / Slack 等平台直接发送
- **`json` 模式**：输出结构化 JSON 数据，适合程序处理或二次开发

## 🔧 集成示例

### 定时任务（Linux Cron）

```bash
# 每天早上 8:30 获取数据并保存到文件
30 8 * * * cd /path/to/script && python github_trending.py --output json >> daily_report.json
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

配合其他工具实现 Webhook 推送：

```bash
# 获取 JSON 数据
DATA=$(python github_trending.py --output json)

# 推送到自建 Server
curl -X POST https://your-server.com/webhook \
  -H "Content-Type: application/json" \
  -d "$DATA"
```

## 📚 数据来源

本项目的数据来源于 [OpenGithubs/github-daily-rank](https://github.com/OpenGithubs/github-daily-rank)，该仓库每天自动爬取 GitHub Trending 数据并计算日/周/月增长量。

| 项目 | 说明 |
|------|------|
| **源仓库** | [OpenGithubs/github-daily-rank](https://github.com/OpenGithubs/github-daily-rank) |
| **数据格式** | `YYYY/MM/YYYYMMDD.md` 预计算排行榜 |
| **更新频率** | 每天早上 ~08:30 CST 更新 |
| **排序方式** | 全语言混合按日增长量排序 |
| **数据字段** | 排名、Star 总数、日/周/月增长、项目描述、开源时间 |

## 📁 项目结构

```
github-trending/
├── github_trending.py    # 主脚本（零依赖）
├── README.md             # 本文件
├── LICENSE               # MIT 许可证
└── .gitignore            # Git 忽略规则
```

## ⚠️ 注意事项

1. **数据延迟**：数据源每天早上 ~08:30 更新，在此之前获取到的是前一天的数据
2. **翻译限流**：Google Translate 免费接口有隐性限流，脚本默认在每次翻译之间添加 0.1s 延迟
3. **网络要求**：需能访问 `raw.githubusercontent.com` 和 `translate.googleapis.com`
4. **中文翻译**：翻译结果仅供参考，部分技术术语可能保留原文更合适

## 🤝 贡献

欢迎提交 Issue 和 PR！如果你有好的想法或改进建议，请随时贡献。

## 📄 许可证

[MIT License](LICENSE) © 2026 Yangsiyu

## 🙏 致谢

- [OpenGithubs/github-daily-rank](https://github.com/OpenGithubs/github-daily-rank) — 提供每日预计算排行榜数据
- [OpenGithubs](https://github.com/OpenGithubs) — GitHub 开源推荐社区