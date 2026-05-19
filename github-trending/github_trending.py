#!/usr/bin/env python3
"""
GitHub Trending Daily — 从 github.com/trending 抓取每日热门项目
============================================================
- 抓取全语言 Trending Top 25
- 保存为 data/YYYY/YYYYMMDD.md 单文件 Markdown 表格
- 提交并推送到 WorkScript 仓库

Usage:
  python3 github_trending.py                          # 今日数据
  python3 github_trending.py --date 20260518           # 指定日期
  python3 github_trending.py --output json             # JSON 输出到 stdout
  python3 github_trending.py --no-save                 # 不保存文件
  python3 github_trending.py --no-push                 # 提交但不推送
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────────────
WORKSCRIPT_DIR = os.path.expanduser("~/WorkScript")
SKILL_DIR = os.path.join(os.path.expanduser("~"), ".hermes", "skills", "github-trending")

# 同时写入 skill 本地 + git 仓库
DATA_DIRS = [
    os.path.join(SKILL_DIR, "data"),
    os.path.join(WORKSCRIPT_DIR, "github-trending", "data"),
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
TRENDING_URL = "https://github.com/trending"
REQ_TIMEOUT = 30


# ─── Helpers ─────────────────────────────────────────────────────────────────

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def format_stars(n):
    """Format star count: 1234 -> '1.2k', 12345 -> '12.3k'."""
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def fetch_url(url):
    """Fetch URL with retry and User-Agent header."""
    headers = {"User-Agent": USER_AGENT}

    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQ_TIMEOUT) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            last_err = e
            eprint(f"[!] Attempt {attempt + 1}/3 failed: {e}")
            time.sleep(1)
    eprint(f"[!] All attempts failed for {url}")
    return ""


# ─── Scrape GitHub Trending ─────────────────────────────────────────────────

def scrape_trending(since="daily"):
    """Scrape github.com/trending page. Returns list of dicts."""
    url = f"{TRENDING_URL}?since={since}"
    eprint(f"[*] Fetching: {url}")

    html = fetch_url(url)
    if not html:
        eprint("[!] Failed to fetch trending page")
        return []

    repos = []
    articles = re.split(r'<article\s+class="Box-row', html)[1:]

    for art in articles:
        try:
            repo = _parse_article(art)
            if repo:
                repos.append(repo)
        except Exception:
            continue

    eprint(f"[✓] Parsed {len(repos)} repos from trending page")
    return repos


def _parse_article(art):
    """Parse a single trending article HTML snippet."""
    # 1. Repo full name
    href_match = re.search(
        r'href="/([^/"]+)/([^/"]+)"[^>]*>\s*$', art, re.MULTILINE
    )
    if not href_match:
        h2_section = re.search(r'<h2[^>]*>(.*?)</h2>', art, re.DOTALL)
        if h2_section:
            href_match = re.search(r'href="/([^/"]+)/([^/"]+)"', h2_section.group(1))

    if not href_match:
        return None

    owner = href_match.group(1)
    repo_name = href_match.group(2)
    full_name = f"{owner}/{repo_name}"
    repo_url = f"https://github.com/{full_name}"

    # 2. Description
    desc_match = re.search(
        r'<p\s+class="col-9[^"]*color-fg-muted[^"]*"[^>]*>\s*(.*?)\s*</p>',
        art, re.DOTALL
    )
    description = ""
    if desc_match:
        desc_text = desc_match.group(1)
        desc_text = re.sub(r'<[^>]+>', '', desc_text).strip()
        description = desc_text

    # 3. Programming language
    lang_match = re.search(
        r'itemprop="programmingLanguage"[^>]*>\s*([^<]+?)\s*<', art
    )
    language = lang_match.group(1).strip() if lang_match else ""

    # 4. Total stars
    stars = 0
    stars_match = re.search(
        r'href="/[^/"]+/[^/"]+/stargazers"[^>]*>.*?</svg>\s*([\d,]+)\s*</a>',
        art, re.DOTALL
    )
    if stars_match:
        stars = int(stars_match.group(1).replace(",", ""))

    # 5. Stars today
    stars_today = 0
    today_match = re.search(r'(\d[\d,]*)\s*stars?\s*today', art)
    if today_match:
        stars_today = int(today_match.group(1).replace(",", ""))

    return {
        "rank": 0,
        "name": full_name,
        "url": repo_url,
        "description": description,
        "language": language,
        "stars": stars,
        "stars_today": stars_today,
    }


# ─── Save Data ───────────────────────────────────────────────────────────────

def save_to_all_dirs(all_repos, date_str):
    """Save markdown file to all configured data directories."""
    saved_files = []
    for base_dir in DATA_DIRS:
        path = _save_md(all_repos, date_str, base_dir)
        if path:
            saved_files.append(path)
    return saved_files


def _save_md(all_repos, date_str, base_dir):
    """Write a single YYYY/YYYYMMDD.md with all repos in table format."""
    year = date_str[:4]
    d = datetime.strptime(date_str, "%Y%m%d")
    date_display = d.strftime("%Y-%m-%d")

    md_dir = os.path.join(base_dir, year)
    os.makedirs(md_dir, exist_ok=True)

    lines = []
    lines.append(f"# GitHub Daily Trending ({date_display})")
    lines.append("")
    lines.append("| # | Repository | Stars | Daily Growth | Description | Language |")
    lines.append("|---| --- | --- | --- | --- | --- |")

    for r in all_repos:
        desc = (r.get("description") or "")[:60].replace("|", "\\|")
        lang = r.get("language") or ""
        lines.append(
            f"| {r['rank']} | [{r['name']}]({r['url']}) | "
            f"{format_stars(r['stars'])} | 🔺{r['stars_today']} | {desc} | {lang} |"
        )

    lines.append("")
    lines.append("*Data from [OpenGithubs/github-daily-rank](https://github.com/OpenGithubs/github-daily-rank)*")

    md_path = os.path.join(md_dir, f"{date_str}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    eprint(f"[✓] Saved: {md_path}")
    return md_path


# ─── Git Operations ──────────────────────────────────────────────────────────

def git_commit_push(date_str):
    """Commit and push trending data to the WorkScript repo."""
    if not os.path.isdir(os.path.join(WORKSCRIPT_DIR, ".git")):
        eprint("[!] Not a git repo")
        return False

    try:
        os.system(f"cd {WORKSCRIPT_DIR} && git add github-trending/data/")

        result = os.popen(f"cd {WORKSCRIPT_DIR} && git status --porcelain").read().strip()
        if not result:
            eprint("[*] No changes to commit")
            return True

        commit_msg = f"chore(github-trending): daily trending data for {date_str}"
        os.system(f'cd {WORKSCRIPT_DIR} && git commit -m "{commit_msg}"')

        eprint("[*] Pushing to origin...")
        ret = os.system(f"cd {WORKSCRIPT_DIR} && git push origin main 2>&1")
        if ret == 0:
            eprint("[✓] Pushed successfully")
        else:
            eprint("[!] Push failed (may need manual push)")
        return True
    except Exception as e:
        eprint(f"[!] Git error: {e}")
        return False


# ─── Format Output ───────────────────────────────────────────────────────────

def format_tg_message(all_repos, date_display):
    """Format trending data as Telegram message."""
    lines = []
    lines.append(f"📊 *GitHub Trending Daily — {date_display}*")
    lines.append("")

    for i, r in enumerate(all_repos):
        lang = r.get("language") or "?"
        desc = (r.get("description") or "")[:80]
        lines.append(
            f"  *{r['rank']}.* `{lang}` [{r['name']}]({r['url']})\n"
            f"     ⭐ {format_stars(r['stars'])}  🔺+{r['stars_today']}\n"
            f"     _{desc}_"
        )

    lines.append("")
    lines.append("───")
    lines.append("_数据来源: [github.com/trending](https://github.com/trending?since=daily)_")

    return "\n".join(lines)


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GitHub Trending Daily")
    parser.add_argument("--date", help="Specify date (YYYYMMDD)")
    parser.add_argument("--output", choices=["tg", "json"], default="tg")
    parser.add_argument("--no-save", action="store_true", help="Skip saving to repo")
    parser.add_argument("--no-push", action="store_true", help="Commit but don't push")
    args = parser.parse_args()

    # Determine date
    if args.date:
        date_str = args.date
        data_date = datetime.strptime(date_str, "%Y%m%d")
    else:
        data_date = datetime.now()
        date_str = data_date.strftime("%Y%m%d")

    date_display = data_date.strftime("%Y-%m-%d")

    # 1. Scrape trending page
    eprint(f"[*] Scraping GitHub Trending for {date_display}...")
    all_repos = scrape_trending()
    if not all_repos:
        eprint("[!] No data fetched")
        sys.exit(1)

    # 2. Sort by stars_today descending
    all_repos = sorted(all_repos, key=lambda x: x["stars_today"], reverse=True)
    for i, r in enumerate(all_repos, 1):
        r["rank"] = i

    eprint(f"[✓] Total repos: {len(all_repos)}")

    # 3. Save data
    if not args.no_save:
        saved = save_to_all_dirs(all_repos, date_str)
        eprint(f"[✓] Saved {len(saved)} files")

        # 4. Git commit & push
        if not args.no_push:
            git_commit_push(date_str)

    # 5. Output
    if args.output == "json":
        print(json.dumps({"date": date_str, "repos": all_repos},
                         ensure_ascii=False, indent=2))
    else:
        print(format_tg_message(all_repos, date_display))


if __name__ == "__main__":
    main()