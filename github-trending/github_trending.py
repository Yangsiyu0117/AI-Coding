#!/usr/bin/env python3
"""
GitHub 每日热门开源项目 — GitHub Trending 爬取版
=================================================
- 爬取 github.com/trending 页面获取 Python、Go 热门项目
- 展示每日 star 增长量、总 star 数、周/月增长
- 输出 OpenGithubs 风格格式
- 保存 markdown 存档到 skill data + WorkScript

Usage:
  python3 github_trending_v2.py                         # 今日数据
  python3 github_trending_v2.py --date 20260519          # 指定日期
  python3 github_trending_v2.py --output tg              # Telegram 格式（默认）
  python3 github_trending_v2.py --output md              # Markdown 格式
  python3 github_trending_v2.py --no-save                # 不保存文件
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta

# ─── Configuration ───────────────────────────────────────────────────────────
TOP_N = 10
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TRENDING_URL = "https://github.com/trending/{lang}?since={since}"
REPO_API = "https://api.github.com/repos/{full_name}"
REQ_TIMEOUT = 30

WORKSCRIPT_DIR = os.path.expanduser("~/WorkScript")
SKILL_DIR = os.path.expanduser("~/.hermes/skills/github-trending")

DATA_DIRS = [
    os.path.join(SKILL_DIR, "data"),
    os.path.join(WORKSCRIPT_DIR, "github-trending", "data"),
]

LANGUAGES = {
    "all": "🌐 All Languages",
}

# ─── Translation Helpers ──────────────────────────────────────────────────────────

_TRANSLATION_CACHE = {}

def translate_to_zh(text):
    """Translate English text to Chinese via Google Translate API (free, no key needed)."""
    if not text or len(text) < 10:
        return text
    # Check if already looks like Chinese
    if re.search(r'[\u4e00-\u9fff]', text):
        return text
    cache_key = text[:100]
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key]
    
    try:
        encoded = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            result = "".join([part[0] for part in data[0] if part[0]])
            _TRANSLATION_CACHE[cache_key] = result
            return result
    except Exception as e:
        eprint(f"[!] Translation failed: {e}")
        return text


# ─── Helpers ─────────────────────────────────────────────────────────────────


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def format_stars(n):
    """1234 -> '1.2k', 12345 -> '12.3k'"""
    if n >= 1000:
        val = n / 1000
        return f"{val:.1f}k"
    return str(n)


def fetch_page(url, token=""):
    """Fetch URL and return text content."""
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=REQ_TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_err = e
            eprint(f"[!] Attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                import time
                time.sleep(2)
    raise last_err


def fetch_repo_details(full_name, token=""):
    """Get repo details from GitHub API."""
    url = REPO_API.format(full_name=full_name)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=REQ_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        eprint(f"[!] API error for {full_name}: {e}")
        return None


def parse_star_count(text):
    """Parse '13,046' -> 13046, '78.7k' -> 78700"""
    text = text.strip()
    if not text:
        return 0
    # Remove commas
    text = text.replace(",", "")
    if "k" in text.lower():
        return int(float(text.lower().replace("k", "")) * 1000)
    if "m" in text.lower():
        return int(float(text.lower().replace("m", "")) * 1000000)
    try:
        return int(text)
    except ValueError:
        return 0


# ─── Scrape Trending Page ────────────────────────────────────────────────────


def scrape_trending(lang, since="daily", token=""):
    """
    Scrape GitHub Trending page for a language.
    
    Returns list of dicts:
    {
        "name": "owner/repo",
        "url": "https://github.com/owner/repo",
        "description": "...",
        "stars_total": 13046 (int),
        "stars_growth": 1439 (int, for the given since period),
        "growth_label": "today" | "this week" | "this month",
    }
    """
    url = TRENDING_URL.format(lang=lang, since=since)
    page = fetch_page(url, token)
    
    # Find all article rows
    articles = re.findall(
        r'<article[^>]*class="Box-row[^"]*"[^>]*>(.*?)</article>',
        page, re.DOTALL
    )
    
    results = []
    for article in articles:
        # Repo name from href
        name_match = re.search(r'href="/([^"/]+/[^"/]+?)"', article)
        if not name_match:
            continue
        full_name = name_match.group(1)
        
        # Skip login/signup links
        if "login" in full_name or "signup" in full_name:
            continue
        
        # Description
        desc_match = re.search(
            r'<p[^>]*class="col-9[^"]*color-fg-muted[^"]*"[^>]*>(.*?)</p>',
            article, re.DOTALL
        )
        description = ""
        if desc_match:
            description = html.unescape(re.sub(r'<[^>]+>', '', desc_match.group(1)).strip())
        
        # Total stars
        stars_total = 0
        stars_match = re.search(
            r'href="/[^/"]+/[^/"]+/stargazers"[^>]*>.*?<svg.*?</svg>\s*([\d,]+(?:\.\d)?[kKmM]?)\s*</a>',
            article, re.DOTALL
        )
        if stars_match:
            stars_total = parse_star_count(stars_match.group(1))
        
        # Growth stars (today / this week / this month)
        growth_pattern = {
            "daily": r'([\d,]+)\s+stars\s+today',
            "weekly": r'([\d,]+)\s+stars\s+this\s+week',
            "monthly": r'([\d,]+)\s+stars\s+this\s+month',
        }
        growth_match = re.search(growth_pattern.get(since, ""), article)
        stars_growth = parse_star_count(growth_match.group(1)) if growth_match else 0
        
        growth_label = {"daily": "today", "weekly": "this week", "monthly": "this month"}.get(since, "today")
        
        results.append({
            "name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": description,
            "stars_total": stars_total,
            "stars_growth": stars_growth,
            "growth_label": growth_label,
        })
    
    return results


# ─── Collect All Data ────────────────────────────────────────────────────────


def is_valid_repo(repo):
    """Filter out non-repo entries like sponsors/* login signup etc."""
    name = repo.get("name", "")
    if not name or "/" not in name:
        return False
    if name.startswith("sponsors/"):
        return False
    if name.startswith("login") or name.startswith("signup"):
        return False
    return True


def collect_trending_data(token=""):
    """
    Scrape GitHub Trending (all languages, daily/weekly/monthly).
    Returns list of enriched repos sorted by daily growth descending.
    """
    eprint("[*] Fetching all languages daily trending...")
    daily = scrape_trending("", "daily", token)
    daily = [r for r in daily if is_valid_repo(r)]
    daily.sort(key=lambda x: x["stars_growth"], reverse=True)
    
    eprint("[*] Fetching all languages weekly trending...")
    weekly = scrape_trending("", "weekly", token)
    weekly = [r for r in weekly if is_valid_repo(r)]
    weekly_lookup = {r["name"]: r["stars_growth"] for r in weekly}
    
    eprint("[*] Fetching all languages monthly trending...")
    monthly = scrape_trending("", "monthly", token)
    monthly = [r for r in monthly if is_valid_repo(r)]
    monthly_lookup = {r["name"]: r["stars_growth"] for r in monthly}
    
    enriched = []
    for repo in daily:
        if repo["stars_growth"] < 5:
            continue
        
        details = fetch_repo_details(repo["name"], token)
        
        created_at = ""
        api_description = repo["description"]
        api_stars = repo["stars_total"]
        
        if details:
            if "message" in details and "API rate limit" in details.get("message", ""):
                eprint(f"[w] Rate limited, using trending data for {repo['name']}")
            elif "message" in details and details.get("message") == "Not Found":
                eprint(f"[w] Repo not found: {repo['name']}, skipping")
                continue
            else:
                created_at_raw = details.get("created_at", "")
                if created_at_raw:
                    try:
                        dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                        created_at = dt.strftime("%Y-%m-%d")
                    except:
                        created_at = created_at_raw[:10]
                
                api_description = details.get("description") or repo["description"]
                api_stars = details.get("stargazers_count", repo["stars_total"])
        
        api_description = translate_to_zh(api_description)
        weekly_growth = weekly_lookup.get(repo["name"], 0)
        monthly_growth = monthly_lookup.get(repo["name"], 0)
        
        enriched.append({
            "name": repo["name"],
            "url": repo["url"],
            "owner": repo["name"].split("/")[0],
            "repo": repo["name"].split("/")[1],
            "language_key": "",
            "language": "",
            "description": api_description[:500],
            "stars_total": api_stars,
            "stars_today": repo["stars_growth"],
            "stars_weekly": weekly_growth,
            "stars_monthly": monthly_growth,
            "created_at": created_at,
        })
    
    # Sort by daily growth descending and assign ranks
    enriched.sort(key=lambda r: r["stars_today"], reverse=True)
    for i, r in enumerate(enriched, 1):
        r["rank"] = i
    
    eprint(f"[✓] Got {len(enriched)} repos")
    return enriched


# ─── Format Output ───────────────────────────────────────────────────────────


def format_number(n):
    """Format number with commas: 3029 -> '3029', 14052 -> '14052'"""
    return f"{n:,}"


def format_open_githubs(repos, date_display):
    """
    Format in OpenGithubs style — single combined Top 10.
    """
    top_repos = repos[:TOP_N]
    
    lines = []
    lines.append(f"📅 GitHub 热门开源项目 | {date_display}")
    lines.append("")
    
    if not top_repos:
        lines.append("⚠️ 暂无数据")
        return "\n".join(lines)
    
    # 🏆 日榜最佳项目
    best = top_repos[0]
    lines.append(f"🏆 日榜最佳项目: [{best['name']}]({best['url']})")
    lines.append(f"   ⭐️ 总星标数量：{format_stars(best['stars_total'])}")
    lines.append(f"   🔺 日增长数量：{best['stars_today']}⭐️")
    lines.append(f"   📝 {best.get('description', '')[:120]}")
    lines.append("")
    
    # ━━━ 📊 日榜排行 ━━━
    lines.append("━━━ 📊 日榜排行 ━━━")
    lines.append("")
    
    # 📊 日榜排行表
    lines.append("| 排名 | 项目名 | Star⭐️ | 今日增长量 |")
    lines.append("|------|--------|--------|-----------|")
    for r in top_repos:
        lines.append(f"| {r['rank']} | [{r['name']}]({r['url']}) | {format_stars(r['stars_total'])} | 🔺{r['stars_today']} |")
    lines.append("")
    
    # ━━━ 📋 日榜项目详情 ━━━
    lines.append("━━━ 📋 日榜项目详情 ━━━")
    lines.append("")
    
    # 📋 日榜项目详情
    for r in top_repos:
        lines.append(f"*#{r['rank']}.* [{r['name']}]({r['url']})")
        lines.append(f"   ⭐️ 总星标数量：{format_stars(r['stars_total'])}")
        lines.append(f"   🔺 日增长数量：{r['stars_today']}⭐️")
        if r['stars_weekly']:
            lines.append(f"   🔺 上周增长数量：{r['stars_weekly']}⭐️")
        if r['stars_monthly']:
            lines.append(f"   🔺 上月增长数量：{r['stars_monthly']}⭐️")
        if r['created_at']:
            lines.append(f"   📅 开源时间：{r['created_at']}")
        lines.append(f"   📝 项目描述：{r.get('description', '')[:200]}")
        lines.append("")
    
    lines.append("_数据来源: GitHub Trending / GitHub API_")
    
    return "\n".join(lines)


# ─── Save Data ───────────────────────────────────────────────────────────────


def format_md(repos, date_display, date_str):
    """Format as markdown file — single Top 10."""
    top_repos = repos[:TOP_N]
    
    lines = []
    lines.append(f"# GitHub 每日热门开源项目 ({date_display})")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    if not top_repos:
        lines.append("⚠️ 暂无数据")
        lines.append("")
        lines.append("---")
        lines.append(f"_数据更新于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
        return "\n".join(lines) + "\n"
    
    # 🏆 最佳项目
    best = top_repos[0]
    lines.append(f"**🏆 日榜最佳项目:** [{best['name']}]({best['url']})")
    lines.append("")
    lines.append(f"- ⭐️ 总星标数量：{format_stars(best['stars_total'])}")
    lines.append(f"- 🔺 日增长数量：{best['stars_today']}⭐")
    lines.append(f"- 📝 项目描述：{best.get('description', '')[:200]}")
    lines.append("")
    
    # 排行表
    lines.append("| 排名 | 项目名 | Star⭐ | 今日增长量 |")
    lines.append("|------|--------|-------|-----------|")
    for r in top_repos:
        lines.append(f"| {r['rank']} | [{r['name']}]({r['url']}) | {format_stars(r['stars_total'])} | 🔺{r['stars_today']} |")
    lines.append("")
    
    # 项目详情
    for r in top_repos:
        lines.append(f"### #{r['rank']}. [{r['name']}]({r['url']})")
        lines.append("")
        lines.append(f"- ⭐️ 总星标数量：{format_stars(r['stars_total'])}")
        lines.append(f"- 🔺 日增长数量：{r['stars_today']}⭐")
        if r['stars_weekly']:
            lines.append(f"- 🔺 上周增长数量：{r['stars_weekly']}⭐")
        if r['stars_monthly']:
            lines.append(f"- 🔺 上月增长数量：{r['stars_monthly']}⭐")
        if r['created_at']:
            lines.append(f"- 📅 开源时间：{r['created_at']}")
        lines.append(f"- 📝 项目描述：{r.get('description', '')[:500]}")
        lines.append("")
    
    lines.append("---")
    lines.append(f"_数据更新于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
    return "\n".join(lines) + "\n"


def save_to_all_dirs(data, date_str, date_display):
    """Save markdown file to all configured data directories."""
    saved_files = []
    md_content = format_md(data, date_display, date_str)
    
    for base_dir in DATA_DIRS:
        year = date_str[:4]
        md_dir = os.path.join(base_dir, year)
        os.makedirs(md_dir, exist_ok=True)
        md_path = os.path.join(md_dir, f"{date_str}.md")
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        eprint(f"[✓] Saved: {md_path}")
        saved_files.append(md_path)
    
    return saved_files


def git_commit_push(date_str):
    """Commit and push to WorkScript repo."""
    repo_dir = WORKSCRIPT_DIR
    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        eprint("[!] Not a git repo")
        return False
    
    try:
        os.system(f"cd {repo_dir} && git add github-trending/data/")
        result = os.popen(f"cd {repo_dir} && git status --porcelain").read().strip()
        if not result:
            eprint("[*] No changes to commit")
            return True
        
        commit_msg = f"chore(github-trending): daily trending data {date_str}"
        os.system(f'cd {repo_dir} && git commit -m "{commit_msg}"')
        
        eprint("[*] Pushing to origin...")
        ret = os.system(f"cd {repo_dir} && git push origin main 2>&1")
        if ret == 0:
            eprint("[✓] Pushed successfully")
        else:
            eprint("[!] Push failed")
        return True
    except Exception as e:
        eprint(f"[!] Git error: {e}")
        return False


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="GitHub 每日热门开源项目")
    parser.add_argument("--date", help="指定日期 (YYYYMMDD)")
    parser.add_argument("--output", choices=["tg", "md", "json"], default="tg",
                        help="输出格式")
    parser.add_argument("--no-save", action="store_true", help="不保存文件")
    parser.add_argument("--no-push", action="store_true", help="不推送远程")
    parser.add_argument("--token", default="", help="GitHub Token")
    args = parser.parse_args()
    
    # Date
    if args.date:
        date_str = args.date
        data_date = datetime.strptime(date_str, "%Y%m%d")
    else:
        data_date = datetime.now()
        date_str = data_date.strftime("%Y%m%d")
    
    date_display = data_date.strftime("%Y.%m.%d")
    token = args.token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    
    # Collect data
    eprint(f"[*] Date: {date_display}")
    eprint(f"[*] Token: {'yes' if token else 'no'}")
    
    data = collect_trending_data(token)
    
    # Output
    if args.output == "json":
        output = json.dumps({"repos": data, "date": date_str, "generated_at": datetime.now().isoformat()}, ensure_ascii=False, indent=2)
    elif args.output == "md":
        output = format_md(data, date_display, date_str)
    else:  # tg
        output = format_open_githubs(data, date_display)
    
    # Save
    if not args.no_save:
        saved = save_to_all_dirs(data, date_str, date_display)
        eprint(f"[✓] Saved {len(saved)} files")
        
        if not args.no_push:
            git_commit_push(date_str)
    
    print(output)


if __name__ == "__main__":
    main()