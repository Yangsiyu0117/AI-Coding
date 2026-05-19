#!/usr/bin/env python3
"""
GitHub Trending Daily — via GitHub Search API
=============================================
- 使用 GitHub Search API 按创建日期查询每日热门项目
- Python Top 10 + Go Top 10
- 单文件格式：data/YYYY/YYYYMMDD.md
- 同步保存到 skill 本地 + WorkScript 仓库
- 自动 git commit & push

Usage:
  python3 github_trending.py                          # 今日数据
  python3 github_trending.py --date 20260519           # 指定日期
  python3 github_trending.py --output json             # JSON 输出到 stdout
  python3 github_trending.py --no-save                 # 不保存文件
  python3 github_trending.py --no-push                 # 不推送远程
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, date, timedelta

# ─── Configuration ───────────────────────────────────────────────────────────
WORKSCRIPT_DIR = os.path.expanduser("~/WorkScript")
SKILL_DIR = os.path.join(os.path.expanduser("~"), ".hermes", "skills", "github-trending")

# 数据目录：同时写入 skill 本地 + git 仓库
DATA_DIRS = [
    os.path.join(SKILL_DIR, "data"),                    # 本地 skill 数据
    os.path.join(WORKSCRIPT_DIR, "github-trending", "data"),  # git 仓库数据
]

TOP_N = 10
USER_AGENT = "github-trending-bot/1.0"
SEARCH_API = "https://api.github.com/search/repositories"
REQ_TIMEOUT = 30

LANGUAGES = ["Python", "Go"]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def format_stars(n):
    """Format star count: 1234 -> '1.2k', 12345 -> '12.3k', 111300 -> '111.3k'."""
    if n >= 1000:
        val = n / 1000
        if val >= 100:
            return f"{val:.1f}k"
        return f"{val:.1f}k"
    return str(n)


def fetch_json(url, token=""):
    """Fetch URL and return parsed JSON."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQ_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            eprint(f"[!] HTTP {e.code} on attempt {attempt + 1}/3: {body[:200]}")
            last_err = e
            if e.code == 403 and "rate limit" in body.lower():
                eprint("[!] Rate limited — waiting 10s...")
                time.sleep(10)
            elif e.code == 422:
                eprint("[!] Bad query, not retrying")
                break
            else:
                time.sleep(2)
        except Exception as e:
            last_err = e
            eprint(f"[!] Attempt {attempt + 1}/3 failed: {e}")
            time.sleep(2)

    if last_err:
        raise last_err
    return None


# ─── Search API ──────────────────────────────────────────────────────────────

def search_repos(language, date_str, token="", per_page=10):
    """
    Search GitHub repos created on the given date for a specific language.
    Returns list of repo dicts sorted by stars descending.
    """
    query = f"language:{language}+created:{date_str}"
    url = f"{SEARCH_API}?q={urllib.request.quote(query)}&sort=stars&order=desc&per_page={per_page}"

    eprint(f"[*] Searching: language={language}, date={date_str}")
    data = fetch_json(url, token)

    if not data or "items" not in data:
        eprint(f"[!] No results for {language}")
        return []

    items = data["items"]
    eprint(f"[✓] {language}: {data.get('total_count', 0)} total, got {len(items)} items")

    repos = []
    for i, item in enumerate(items, 1):
        # For repos created today, stars_today ≈ total stars
        stars_today = item.get("stargazers_count", 0)

        repos.append({
            "rank": i,
            "name": item.get("full_name", ""),
            "url": item.get("html_url", ""),
            "owner": item.get("owner", {}).get("login", ""),
            "repo": item.get("name", ""),
            "language": language,
            "description": (item.get("description") or "")[:100],
            "stars": item.get("stargazers_count", 0),
            "stars_today": stars_today,
            "forks": item.get("forks_count", 0),
            "created_at": item.get("created_at", ""),
        })

    return repos


# ─── Save Data ───────────────────────────────────────────────────────────────

def save_to_all_dirs(python_repos, go_repos, date_str):
    """Save markdown file to all configured data directories."""
    saved_files = []
    for base_dir in DATA_DIRS:
        f = _save_to_dir(python_repos, go_repos, date_str, base_dir)
        saved_files.append(f)
    return saved_files


def _save_to_dir(python_repos, go_repos, date_str, base_dir):
    """Save single markdown file with both language sections."""
    year = date_str[:4]
    d = datetime.strptime(date_str, "%Y%m%d")
    date_display = d.strftime("%Y-%m-%d")

    md_dir = os.path.join(base_dir, year)
    os.makedirs(md_dir, exist_ok=True)
    md_path = os.path.join(md_dir, f"{date_str}.md")

    lines = []
    lines.append(f"# GitHub Daily Trending ({date_display})")
    lines.append("")

    # ── Python Top 10 ──
    lines.append("## 🐍 Python Top 10")
    lines.append("")
    lines.append("| # | Repository | Stars | Daily Growth | Description |")
    lines.append("|---| --- | --- | --- | --- |")

    for r in python_repos:
        desc = (r.get("description") or "")[:80].replace("|", "\\|")
        lines.append(
            f"| {r['rank']} | [{r['name']}]({r['url']}) | "
            f"{format_stars(r['stars'])} | 🔺{r['stars_today']} | {desc} |"
        )

    lines.append("")

    # ── Go Top 10 ──
    lines.append("## 🔵 Go Top 10")
    lines.append("")
    lines.append("| # | Repository | Stars | Daily Growth | Description |")
    lines.append("|---| --- | --- | --- | --- |")

    for r in go_repos:
        desc = (r.get("description") or "")[:80].replace("|", "\\|")
        lines.append(
            f"| {r['rank']} | [{r['name']}]({r['url']}) | "
            f"{format_stars(r['stars'])} | 🔺{r['stars_today']} | {desc} |"
        )

    lines.append("")
    lines.append("*Data from [GitHub Search API](https://docs.github.com/en/rest/search)*")

    content = "\n".join(lines) + "\n"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)

    eprint(f"[✓] Saved: {md_path}")
    return md_path


# ─── Git Operations ──────────────────────────────────────────────────────────

def git_commit_push(date_str):
    """Commit and push trending data to the WorkScript repo."""
    repo_dir = WORKSCRIPT_DIR

    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        eprint(f"[!] Not a git repo: {repo_dir}")
        return False

    try:
        os.system(f"cd {repo_dir} && git add github-trending/data/")

        result = os.popen(f"cd {repo_dir} && git status --porcelain").read().strip()
        if not result:
            eprint("[*] No changes to commit")
            return True

        commit_msg = f"chore(github-trending): daily trending data for {date_str}"
        os.system(f'cd {repo_dir} && git commit -m "{commit_msg}"')

        eprint("[*] Pushing to origin...")
        ret = os.system(f"cd {repo_dir} && git push origin main 2>&1")
        if ret == 0:
            eprint("[✓] Pushed successfully")
        else:
            eprint("[!] Push failed (may need manual push)")
        return True
    except Exception as e:
        eprint(f"[!] Git error: {e}")
        return False


# ─── Format Output ───────────────────────────────────────────────────────────

def format_tg_message(python_repos, go_repos, date_display):
    """Format trending data as Telegram message."""
    lines = []
    lines.append(f"📊 *GitHub Trending Daily — {date_display}*")
    lines.append("")

    # Python
    if python_repos:
        lines.append("━━━ 🐍 *Python Top 10* ━━━")
        lines.append("")
        for r in python_repos:
            desc = (r.get("description") or "")[:80]
            lines.append(
                f"  *{r['rank']}.* [{r['name']}]({r['url']})\n"
                f"     ⭐ {format_stars(r['stars'])}  🔺+{r['stars_today']}\n"
                f"     _{desc}_"
            )
        lines.append("")

    # Go
    if go_repos:
        lines.append("━━━ 🔵 *Go Top 10* ━━━")
        lines.append("")
        for r in go_repos:
            desc = (r.get("description") or "")[:80]
            lines.append(
                f"  *{r['rank']}.* [{r['name']}]({r['url']})\n"
                f"     ⭐ {format_stars(r['stars'])}  🔺+{r['stars_today']}\n"
                f"     _{desc}_"
            )
        lines.append("")

    lines.append("───")
    lines.append("_数据来源: [GitHub Search API](https://docs.github.com/en/rest/search)_")
    return "\n".join(lines)


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GitHub Trending Daily via Search API")
    parser.add_argument("--date", help="Specify date (YYYYMMDD)")
    parser.add_argument("--output", choices=["tg", "json", "md"], default="tg")
    parser.add_argument("--no-save", action="store_true", help="Skip saving files")
    parser.add_argument("--no-push", action="store_true", help="Commit but don't push")
    parser.add_argument("--token", default="", help="GitHub API token")
    args = parser.parse_args()

    # Determine date
    if args.date:
        date_str = args.date
        data_date = datetime.strptime(date_str, "%Y%m%d")
    else:
        data_date = datetime.now()
        date_str = data_date.strftime("%Y%m%d")

    date_display = data_date.strftime("%Y.%m.%d")

    # Get token from args or env
    token = args.token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""

    # ── Search API ──
    python_repos = search_repos("Python", date_str, token, per_page=TOP_N)
    go_repos = search_repos("Go", date_str, token, per_page=TOP_N)

    # Re-number ranks
    for i, r in enumerate(python_repos, 1):
        r["rank"] = i
    for i, r in enumerate(go_repos, 1):
        r["rank"] = i

    eprint(f"[✓] Python: {len(python_repos)} repos, Go: {len(go_repos)} repos")

    # ── Save ──
    if not args.no_save:
        saved = save_to_all_dirs(python_repos, go_repos, date_str)
        eprint(f"[✓] Saved {len(saved)} files")

        if not args.no_push:
            git_commit_push(date_str)

    # ── Output ──
    if args.output == "json":
        output = json.dumps({
            "date": date_str,
            "python_top": python_repos,
            "go_top": go_repos,
        }, ensure_ascii=False, indent=2)
    elif args.output == "md":
        # Reconstruct markdown for stdout
        lines = [f"# GitHub Daily Trending ({date_display})", ""]
        for lang_name, repos in [("🐍 Python", python_repos), ("🔵 Go", go_repos)]:
            lines.append(f"## {lang_name} Top 10")
            lines.append("")
            lines.append("| # | Repository | Stars | Daily Growth | Description |")
            lines.append("|---| --- | --- | --- | --- |")
            for r in repos:
                desc = (r.get("description") or "")[:80].replace("|", "\\|")
                lines.append(
                    f"| {r['rank']} | [{r['name']}]({r['url']}) | "
                    f"{format_stars(r['stars'])} | 🔺{r['stars_today']} | {desc} |"
                )
            lines.append("")
        lines.append("*Data from [GitHub Search API](https://docs.github.com/en/rest/search)*")
        output = "\n".join(lines) + "\n"
    else:
        output = format_tg_message(python_repos, go_repos, date_display)

    print(output)


if __name__ == "__main__":
    main()