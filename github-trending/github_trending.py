#!/usr/bin/env python3
"""
GitHub Trending Daily — 直接从 github.com/trending 抓取数据
===========================================================
- 抓取全语言 Top 25 + Python Top 10 + Go Top 10
- 保存到 WorkScript 仓库 (github-trending/data/)
- 输出 Telegram 格式消息

Usage:
  python3 github_trending.py                          # 今日数据
  python3 github_trending.py --date 20260518           # 指定日期
  python3 github_trending.py --output json             # JSON 输出
  python3 github_trending.py --no-save                 # 不保存文件
  python3 github_trending.py --no-push                 # 不推送到远程
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, date, timedelta
from collections import defaultdict

# ─── Configuration ───────────────────────────────────────────────────────────
WORKSCRIPT_DIR = os.path.expanduser("~/WorkScript")
SKILL_DIR = os.path.join(os.path.expanduser("~"), ".hermes", "skills", "github-trending")

# 数据目录：同时写入 skill 本地 + git 仓库
DATA_DIRS = [
    os.path.join(SKILL_DIR, "data"),                    # 本地 skill 数据
    os.path.join(WORKSCRIPT_DIR, "github-trending", "data"),  # git 仓库数据
]

TOP_N = 10
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


def fetch_url(url, token=""):
    """Fetch URL with retry and User-Agent header."""
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"

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

def scrape_trending(lang="", since="daily"):
    """
    Scrape github.com/trending page.
    lang: empty for all, "python", "go", etc.
    since: "daily", "weekly", "monthly"
    Returns list of dicts.
    """
    url = f"{TRENDING_URL}/{lang}" if lang else TRENDING_URL
    url += f"?since={since}"
    eprint(f"[*] Fetching: {url}")

    html = fetch_url(url)
    if not html:
        eprint(f"[!] Failed to fetch {url}")
        return []

    repos = []

    # Split by article.Box-row
    articles = re.split(r'<article\s+class="Box-row', html)[1:]

    for art in articles:
        try:
            repo = _parse_article(art)
            if repo:
                repos.append(repo)
        except Exception as e:
            # Skip malformed entries
            continue

    eprint(f"[✓] Parsed {len(repos)} repos from trending page")
    return repos


def _parse_article(art):
    """
    Parse a single trending article HTML snippet.
    Current GitHub HTML structure (2025+):
      <h2>
        <a href="/owner/repo">
          <span class="text-normal">owner /</span>
          repo_name
        </a>
      </h2>
      <p class="col-9 color-fg-muted">description</p>
      <div class="f6 color-fg-muted">
        <span itemprop="programmingLanguage">Language</span>
        <a href=".../stargazers">STARS</a>
        <a href=".../forks">FORKS</a>
        <span>X stars today</span>
      </div>
    """

    # 1. Extract repo full name from href="/owner/repo" inside h2
    #    Find the first href that matches /owner/repo pattern
    href_match = re.search(
        r'href="/([^/"]+)/([^/"]+)"[^>]*>\s*$',
        art,
        re.MULTILINE
    )
    if not href_match:
        # Try alternative: look for href in <a> inside <h2>
        h2_section = re.search(r'<h2[^>]*>(.*?)</h2>', art, re.DOTALL)
        if h2_section:
            h2_content = h2_section.group(1)
            href_match = re.search(r'href="/([^/"]+)/([^/"]+)"', h2_content)

    if not href_match:
        return None

    owner = href_match.group(1)
    repo_name = href_match.group(2)
    full_name = f"{owner}/{repo_name}"
    repo_url = f"https://github.com/{full_name}"

    # 2. Description: <p class="col-9 color-fg-muted"> ... </p>
    desc_match = re.search(
        r'<p\s+class="col-9[^"]*color-fg-muted[^"]*"[^>]*>\s*(.*?)\s*</p>',
        art,
        re.DOTALL
    )
    description = ""
    if desc_match:
        desc_text = desc_match.group(1)
        desc_text = re.sub(r'<[^>]+>', '', desc_text).strip()
        description = desc_text

    # 3. Programming language
    lang_match = re.search(
        r'itemprop="programmingLanguage"[^>]*>\s*([^<]+?)\s*<',
        art
    )
    language = lang_match.group(1).strip() if lang_match else None

    # 4. Total stars — from <a href=".../stargazers">...STARS_TEXT...</a>
    stars = 0
    stars_match = re.search(
        r'href="/[^/"]+/[^/"]+/stargazers"[^>]*>.*?</svg>\s*([\d,]+)\s*</a>',
        art,
        re.DOTALL
    )
    if stars_match:
        stars = int(stars_match.group(1).replace(",", ""))

    # 5. Stars today — from "X stars today" text
    stars_today = 0
    today_match = re.search(r'(\d[\d,]*)\s*stars?\s*today', art)
    if today_match:
        stars_today = int(today_match.group(1).replace(",", ""))

    # 6. Forks
    forks = 0
    forks_match = re.search(
        r'href="/[^/"]+/[^/"]+/forks"[^>]*>.*?</svg>\s*([\d,]+)\s*</a>',
        art,
        re.DOTALL
    )
    if forks_match:
        forks = int(forks_match.group(1).replace(",", ""))

    return {
        "rank": 0,  # Will be set later
        "name": full_name,
        "url": repo_url,
        "owner": owner,
        "repo": repo_name,
        "language": language,
        "description": description,
        "stars": stars,
        "stars_today": stars_today,
        "forks": forks,
    }


# ─── GitHub API enrichment ───────────────────────────────────────────────────

def fetch_github_api(repo_full_name, token=""):
    """Fetch repo metadata from GitHub REST API (no auth needed for public)."""
    url = f"https://api.github.com/repos/{repo_full_name}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "description": data.get("description") or "",
            "language": data.get("language"),
            "created_at": data.get("created_at", ""),
            "topics": data.get("topics", []),
        }
    except Exception as e:
        eprint(f"[!] API error for {repo_full_name}: {e}")
        return None


def enrich_repos(repos, token=""):
    """Enrich repos with additional info from GitHub API (top 25 only)."""
    for i, repo in enumerate(repos[:25]):
        try:
            info = fetch_github_api(repo["name"], token)
            if info:
                repo["stars"] = info["stars"]
                repo["description"] = info["description"] or repo["description"]
                repo["created_at"] = info["created_at"]
                repo["forks"] = info["forks"]
                repo["topics"] = info["topics"]
                if info["language"]:
                    repo["language"] = info["language"]
            # Small delay to avoid rate limiting
            time.sleep(0.15)
        except Exception as e:
            eprint(f"[!] Skipping API for {repo['name']}: {e}")
            continue
    return repos


# ─── Save Data ───────────────────────────────────────────────────────────────

def save_to_all_dirs(all_repos, lang_repos, date_str):
    """Save data to all configured data directories."""
    saved_files = []
    for base_dir in DATA_DIRS:
        files = _save_to_dir(all_repos, lang_repos, date_str, base_dir)
        saved_files.extend(files)
    return saved_files


def _save_to_dir(all_repos, lang_repos, date_str, base_dir):
    """Save repos to a specific base directory in multiple formats."""
    year = date_str[:4]
    month = date_str[4:6]

    d = datetime.strptime(date_str, "%Y%m%d")
    date_display = d.strftime("%Y-%m-%d")

    saved = []

    # 1. Save raw JSON (all languages)
    raw_dir = os.path.join(base_dir, "raw", year, month)
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, f"{date_str}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_str,
            "source": "github.com/trending?since=daily",
            "repos": all_repos
        }, f, ensure_ascii=False, indent=2)
    saved.append(raw_path)

    # 2. Save per-language markdown files (Python, Go)
    for lang, lang_key in [("Python", "python"), ("Go", "go")]:
        repos = lang_repos.get(lang, [])
        if not repos:
            continue

        lang_dir = os.path.join(base_dir, lang_key)
        os.makedirs(lang_dir, exist_ok=True)

        lines = []
        lines.append(f"# GitHub Trending ({date_display}) — {lang} Top {TOP_N}")
        lines.append("")
        lines.append(f"_{lang} 热门开源项目 Top {TOP_N}_")
        lines.append("")
        lines.append("| 排名 | 项目名 | Star⭐ | 今日增长量 | 描述 |")
        lines.append("|------|--------|-------|-----------|------|")

        for r in repos:
            desc = (r.get("description") or "")[:60].replace("|", "\\|")
            lines.append(
                f"| {r['rank']} | [{r['name']}]({r['url']}) | "
                f"{format_stars(r['stars'])} | 🔺{r['stars_today']} | {desc} |"
            )

        lines.append("")
        lines.append(f"_数据来源: [github.com/trending](https://github.com/trending?since=daily)_")

        md_path = os.path.join(lang_dir, f"{date_str}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        saved.append(md_path)

    # 3. Save combined JSON (Python + Go)
    combined = {
        "date": date_str,
        "python_top": lang_repos.get("Python", []),
        "go_top": lang_repos.get("Go", []),
    }
    combined_path = os.path.join(base_dir, f"{date_str}.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    saved.append(combined_path)

    return saved


# ─── Git Operations ──────────────────────────────────────────────────────────

def git_commit_push(date_str):
    """Commit and push trending data to the WorkScript repo."""
    repo_dir = WORKSCRIPT_DIR
    data_dir = os.path.join(repo_dir, "github-trending", "data")

    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        eprint(f"[!] Not a git repo: {repo_dir}")
        return False

    try:
        # Stage changes
        os.system(f"cd {repo_dir} && git add github-trending/data/")

        # Check if anything changed
        result = os.popen(f"cd {repo_dir} && git status --porcelain").read().strip()
        if not result:
            eprint("[*] No changes to commit")
            return True

        # Commit
        commit_msg = f"chore(github-trending): daily trending data for {date_str}"
        os.system(f'cd {repo_dir} && git commit -m "{commit_msg}"')

        # Push
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

def format_tg_message(all_repos, lang_repos, date_display):
    """Format trending data as Telegram message."""
    lines = []

    # Header
    lines.append(f"📊 *GitHub Trending Daily — {date_display}*")
    lines.append("")

    # Python Top 10
    py_repos = lang_repos.get("Python", [])
    if py_repos:
        lines.append("━━━ 🐍 *Python Top 10* ━━━")
        lines.append("")
        for r in py_repos:
            desc = (r.get("description") or "")[:80]
            lines.append(
                f"  *{r['rank']}.* [{r['name']}]({r['url']})\n"
                f"     ⭐ {format_stars(r['stars'])}  🔺+{r['stars_today']}\n"
                f"     _{desc}_"
            )
        lines.append("")

    # Go Top 10
    go_repos = lang_repos.get("Go", [])
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

    # Overall top 5 highlights
    if all_repos:
        lines.append("━━━ 🌟 *全语言 Top 5* ━━━")
        lines.append("")
        for r in all_repos[:5]:
            lang = r.get("language") or "?"
            lines.append(f"  *{r['rank']}.* `{lang}` [{r['name']}]({r['url']}) — 🔺+{r['stars_today']}")
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

    # 1. Scrape trending page (all languages)
    eprint(f"[*] Scraping GitHub Trending for {date_display}...")
    all_repos = scrape_trending(lang="", since="daily")
    if not all_repos:
        eprint("[!] No data fetched from trending page")
        sys.exit(1)

    # 2. Enrich with GitHub API
    token = args.token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if token:
        eprint("[*] Enriching with GitHub API...")
        all_repos = enrich_repos(all_repos, token)

    # 3. Sort all_repos by stars_today descending
    all_repos = sorted(all_repos, key=lambda x: x["stars_today"], reverse=True)
    for i, r in enumerate(all_repos, 1):
        r["rank"] = i

    # 4. Split by language (deep copy to avoid rank cross-contamination)
    lang_repos = defaultdict(list)
    for r in all_repos:
        lang = r.get("language") or "Unknown"
        lang_repos[lang].append(dict(r))  # shallow copy is fine for our fields

    for lang in list(lang_repos.keys()):
        lang_repos[lang] = lang_repos[lang][:TOP_N]
        for i, r in enumerate(lang_repos[lang], 1):
            r["rank"] = i

    eprint(f"[✓] Languages found: {', '.join(sorted(lang_repos.keys(), key=lambda k: len(lang_repos[k]), reverse=True)[:5])}...")
    eprint(f"[✓] Python: {len(lang_repos.get('Python', []))} repos")
    eprint(f"[✓] Go: {len(lang_repos.get('Go', []))} repos")

    # 4. Save data (to both skill dir and WorkScript)
    if not args.no_save:
        saved = save_to_all_dirs(all_repos, lang_repos, date_str)
        eprint(f"[✓] Saved {len(saved)} files across {len(DATA_DIRS)} directories")

        # 5. Git commit & push
        if not args.no_push:
            git_commit_push(date_str)

    # 6. Output
    if args.output == "json":
        output = json.dumps({
            "date": date_str,
            "all_top": all_repos[:TOP_N],
            "python_top": lang_repos.get("Python", []),
            "go_top": lang_repos.get("Go", []),
        }, ensure_ascii=False, indent=2)
    else:
        output = format_tg_message(all_repos, lang_repos, date_display)

    print(output)


if __name__ == "__main__":
    main()