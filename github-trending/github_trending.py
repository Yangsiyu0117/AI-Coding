#!/usr/bin/env python3
"""
GitHub Trending — Fetch daily hot projects from github-daily-rank repo
====================================================================
Fetches data from OpenGithubs/github-daily-rank (pre-computed daily rank).
Output format matches the reference project exactly.
Translates descriptions to Chinese.

Usage:
  python github_trending.py                          # output Telegram message
  python github_trending.py --date 20260518           # specific date
  python github_trending.py --output json             # JSON output
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, date, timedelta

# ─── Configuration ───────────────────────────────────────────────────────────

RAW_BASE = "https://raw.githubusercontent.com/OpenGithubs/github-daily-rank/main"
REPO_API = "https://api.github.com/repos/OpenGithubs/github-daily-rank/contents"
TOP_N = 10
USER_AGENT = "github-trending-bot/1.0"

# ─── Helpers ─────────────────────────────────────────────────────────────────


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def format_stars(num):
    """Format star count: 1000 -> 1k, 10500 -> 10.5k"""
    if num is None:
        return "?"
    if num >= 1000:
        return f"{num / 1000:.1f}k"
    return str(num)


def parse_stars(text):
    """Parse star string like '78.7k' or '78661' to int."""
    if not text:
        return 0
    text = text.strip().replace(",", "").replace("⭐", "").replace("🔺", "")
    if "k" in text.lower():
        return int(float(text.lower().replace("k", "")) * 1000)
    try:
        return int(text)
    except ValueError:
        return 0


def translate_text(text, target="zh-CN"):
    """Translate text to Chinese via Google Translate free HTTP API."""
    if not text or len(text.strip()) == 0:
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = urllib.parse.urlencode({
            "client": "gtx",
            "sl": "auto",
            "tl": target,
            "dt": "t",
            "q": text[:5000],
        })
        req = urllib.request.Request(f"{url}?{params}", headers={
            "User-Agent": USER_AGENT,
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            data = json.loads(raw)
            result = "".join(part[0] for part in data[0])
            return result if result else text
    except Exception as e:
        eprint(f"[!] Translation failed: {e}")
        return text


def fetch_url(url, retries=3):
    """Fetch a URL with retry logic."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            body = e.read().decode()
            eprint(f"[!] HTTP {e.code}: {body[:200]}")
            return None
        except (urllib.error.URLError, TimeoutError) as e:
            eprint(f"[!] Network error: {e}")
            if attempt < retries - 1:
                time.sleep(5)
                continue
            return None
    return None


# ─── Fetch data from github-daily-rank ──────────────────────────────────────


def find_latest_date():
    """Find the latest available date with data in the repo."""
    today = date.today()
    # Try today, then go back up to 7 days
    for days_back in range(7):
        d = today - timedelta(days=days_back)
        date_str = d.strftime("%Y%m%d")
        url = f"{RAW_BASE}/{d.strftime('%Y/%m')}/{date_str}.md"
        content = fetch_url(url)
        if content:
            eprint(f"[✓] Found data: {d.strftime('%Y.%m.%d')}")
            return date_str, content, d
    return None, None, None


def fetch_by_date(date_str):
    """Fetch data for a specific date string (YYYYMMDD)."""
    d = datetime.strptime(date_str, "%Y%m%d").date()
    url = f"{RAW_BASE}/{d.strftime('%Y/%m')}/{date_str}.md"
    content = fetch_url(url)
    if content:
        return date_str, content, d
    return None, None, None


# ─── Parse markdown content ─────────────────────────────────────────────────


def parse_rank_table(content):
    """
    Parse the rank table from markdown content.
    Returns list of dicts: {rank, name, url, stars, daily_growth}
    """
    repos = []

    # Find the table section - look for the markdown table pattern
    # | 排名 | 项目名 | Star⭐ | 今日增长量 |
    # | 1 | [owner/repo](url) | Xk | 🔺Y |
    table_pattern = re.compile(
        r'\|\s*(\d+)\s*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([^\|]+)\s*\|\s*([^\|]+?)(?:\s*\||\s*$)',
        re.MULTILINE
    )

    for match in table_pattern.finditer(content):
        rank = int(match.group(1))
        name = match.group(2).strip()
        url = match.group(3).strip()
        stars_raw = match.group(4).strip()
        growth_raw = match.group(5).strip()

        if rank > TOP_N:
            continue

        # Parse growth
        growth_str = growth_raw.replace("🔺", "").strip()
        daily_growth = parse_stars(growth_str)

        repos.append({
            "rank": rank,
            "name": name,
            "url": url,
            "stars": parse_stars(stars_raw),
            "stars_display": stars_raw,
            "daily_growth": daily_growth,
            "daily_growth_display": growth_raw,
        })

    return repos


def parse_project_details(content, repos):
    """
    Parse individual project details from the markdown.
    Extracts weekly_growth, monthly_growth, created_at, description.
    Matches by rank number and repo URL.
    """
    # Split by project sections (h3 tags mark each project)
    # Pattern: <h3...>N.  https://github.com/...</h3>
    sections = re.split(r'<h3[^>]*>', content)

    for section in sections:
        # Match: N.  https://github.com/owner/repo
        header_match = re.search(
            r'(\d+)\.\s+https://github\.com/([^\s<]+)',
            section
        )
        if not header_match:
            continue

        rank = int(header_match.group(1))
        repo_path = header_match.group(2).strip()

        if rank < 1 or rank > TOP_N:
            continue

        # Find matching repo
        repo = next((r for r in repos if r["rank"] == rank), None)
        if not repo:
            continue

        # Extract fields
        weekly = re.search(r'🔺\s*上周增长数量：([^⭐]+)⭐', section)
        monthly = re.search(r'🔺\s*上月增长数量：([^⭐]+)⭐', section)
        created = re.search(r'📅\s*开源时间：([^\n]+)', section)
        desc = re.search(r'📝\s*项目描述：([^\n]*)', section)

        repo["weekly_growth"] = parse_stars(weekly.group(1).strip()) if weekly else 0
        repo["monthly_growth"] = parse_stars(monthly.group(1).strip()) if monthly else 0
        repo["created_at"] = created.group(1).strip() if created else ""
        repo["description"] = desc.group(1).strip() if desc and desc.group(1).strip() else ""

    return repos


# ─── Formatting ──────────────────────────────────────────────────────────────


def format_tg_message(repos, date_display):
    """Format exactly matching the reference project's output style."""
    lines = []

    # Header
    lines.append(f"📅 *GitHub 热门开源项目* | {date_display}")
    lines.append("")

    # ── Best project highlight ──
    best = repos[0] if repos else None
    if best:
        lines.append(f"🏆 *日榜最佳项目:* [{best['name']}]({best['url']})")
        lines.append(f"   ⭐ 总星标数量：{format_stars(best['stars'])}")
        lines.append(f"   🔺 日增长数量：{best['daily_growth']}⭐")
        lines.append(f"   📝 {best.get('description', '')}")
        lines.append("")

    # ── Rank table ──
    lines.append("━━━ 📊 日榜排行 ━━━")
    lines.append("")
    lines.append("| 排名 | 项目名 | Star⭐ | 今日增长量 |")
    lines.append("|------|--------|-------|-----------|")

    for repo in repos:
        growth_display = repo.get("daily_growth_display", f"🔺{repo['daily_growth']}")
        lines.append(
            f"| {repo['rank']} | [{repo['name']}]({repo['url']}) | "
            f"{format_stars(repo['stars'])} | {growth_display} |"
        )

    lines.append("")

    # ── Project Details ──
    lines.append("━━━ 📋 日榜项目详情 ━━━")
    lines.append("")

    for repo in repos:
        lines.append(f"*#{repo['rank']}.* [{repo['name']}]({repo['url']})")

        lines.append(f"   ⭐ 总星标数量：{format_stars(repo['stars'])}")

        dg = repo["daily_growth"]
        lines.append(f"   🔺 日增长数量：{dg}⭐" if dg else "   🔺 日增长数量：暂无数据")

        wg = repo.get("weekly_growth")
        if wg and wg > 0:
            lines.append(f"   🔺 上周增长数量：{wg}⭐")
        else:
            lines.append(f"   🔺 上周增长数量：暂无数据")

        mg = repo.get("monthly_growth")
        if mg and mg > 0:
            lines.append(f"   🔺 上月增长数量：{mg}⭐")
        else:
            lines.append(f"   🔺 上月增长数量：暂无数据")

        created = repo.get("created_at", "")
        if created:
            lines.append(f"   📅 开源时间：{created}")
        else:
            lines.append(f"   📅 开源时间：未知")

        desc = repo.get("description", "")
        if desc:
            desc_short = desc if len(desc) <= 150 else desc[:147] + "..."
            lines.append(f"   📝 项目描述：{desc_short}")

        lines.append("")

    lines.append("───")
    lines.append("_数据来源: [OpenGithubs/github-daily-rank](https://github.com/OpenGithubs/github-daily-rank)_")

    return "\n".join(lines)


def format_json_output(repos, date_str):
    """Format output as JSON."""
    items = []
    for repo in repos:
        items.append({
            "rank": repo["rank"],
            "full_name": repo["name"],
            "url": repo["url"],
            "stars": repo["stars"],
            "stars_display": format_stars(repo["stars"]),
            "daily_growth": repo["daily_growth"],
            "weekly_growth": repo.get("weekly_growth"),
            "monthly_growth": repo.get("monthly_growth"),
            "created_at": repo.get("created_at", ""),
            "description": repo.get("description", ""),
        })
    return json.dumps({"date": date_str, "top_10": items}, ensure_ascii=False, indent=2)


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Fetch GitHub daily trending from github-daily-rank"
    )
    parser.add_argument(
        "--date", help="Specific date (YYYYMMDD format, default: latest available)"
    )
    parser.add_argument(
        "--output", choices=["tg", "json"], default="tg",
        help="Output format: tg (Telegram) or json"
    )
    parser.add_argument(
        "--no-translate", action="store_true",
        help="Skip translation (keep original English descriptions)"
    )
    args = parser.parse_args()

    # ── Fetch data ──
    if args.date:
        date_str, content, data_date = fetch_by_date(args.date)
        if not content:
            eprint(f"[!] No data found for date: {args.date}")
            sys.exit(1)
    else:
        date_str, content, data_date = find_latest_date()
        if not content:
            eprint("[!] No data found in github-daily-rank repo")
            sys.exit(1)

    date_display = data_date.strftime("%Y.%m.%d")

    # ── Parse ──
    repos = parse_rank_table(content)
    repos = parse_project_details(content, repos)
    eprint(f"[✓] Parsed {len(repos)} projects from {date_display}")

    if not repos:
        eprint("[!] No projects found in the data")
        sys.exit(1)

    # ── Translate descriptions ──
    if not args.no_translate:
        eprint("[*] Translating descriptions to Chinese...")
        for repo in repos:
            desc = repo.get("description", "")
            if desc and re.search(r'[a-zA-Z]', desc):
                repo["description"] = translate_text(desc)
                time.sleep(0.1)

    # ── Output ──
    if args.output == "json":
        print(format_json_output(repos, date_str))
    else:
        print(format_tg_message(repos, date_display))


if __name__ == "__main__":
    main()