"""新闻采集：周刊 + 每日多源聚合"""
import json
import os
import re
import ssl
import time
from difflib import SequenceMatcher
from urllib.request import urlopen, Request

HEADERS = {"User-Agent": "DailyTechBriefing/1.0"}
REPO_RAW = "https://raw.githubusercontent.com/ruanyf/weekly/master"
LAST_WEEKLY_FILE = ".weekly-tracker/last_weekly.txt"
MAX_RETRIES = 3
RETRY_DELAY = 2


def _fetch(url, retries=MAX_RETRIES, parse_json=True):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for attempt in range(retries):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=20, context=ctx) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if parse_json else data
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"  [fetch] {url[:80]}... 失败: {e}")
                return None


def _fetch_text(url):
    return _fetch(url, parse_json=False)


def _get_last_weekly_num():
    try:
        return int(open(LAST_WEEKLY_FILE).read().strip())
    except Exception:
        return 0


def _save_last_weekly_num(num):
    os.makedirs(os.path.dirname(LAST_WEEKLY_FILE), exist_ok=True)
    with open(LAST_WEEKLY_FILE, "w") as f:
        f.write(str(num))


def _strip_markdown(text):
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _title_sim(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(items, threshold=0.6):
    seen = []
    for item in items:
        if not any(_title_sim(item["title"], s["title"]) > threshold for s in seen):
            seen.append(item)
    return seen


# ─── 周刊 ───────────────────────────────────────

def fetch_weekly_if_new():
    """如果有新的周刊则返回，否则返回 None"""
    readme = _fetch_text(f"{REPO_RAW}/README.md")
    if not readme:
        return None

    m = re.search(r'第\s*(\d+)\s*期[：:]\s*[^]]*\]\(([^)]+)\)', readme)
    if not m:
        return None

    issue_num = int(m.group(1))
    last = _get_last_weekly_num()

    if issue_num <= last:
        print(f"  周刊未更新（第{issue_num}期已读，上次第{last}期）")
        return None

    issue_url = f"{REPO_RAW}/{m.group(2)}"
    content = _fetch_text(issue_url)
    if not content:
        return None

    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else f"科技爱好者周刊 第{issue_num}期"

    body = _strip_markdown(content)
    body = re.sub(r'^.*?\n', '', body, count=1).strip()
    if len(body) > 8000:
        body = body[:8000] + "\n\n（内容过长已截断）"

    _save_last_weekly_num(issue_num)
    print(f"  发现新周刊：第{issue_num}期")

    return [{
        "title": title,
        "url": f"https://github.com/ruanyf/weekly/blob/master/docs/issue-{issue_num}.md",
        "source": f"科技爱好者周刊 第{issue_num}期",
        "body": body,
    }]


# ─── 每日来源 ───────────────────────────────────

def fetch_weibo_hot():
    """微博热搜"""
    data = _fetch("https://weibo.com/ajax/side/hotSearch")
    if not data:
        return []
    results = []
    for item in data.get("data", {}).get("realtime", [])[:15]:
        word = item.get("word", "") or item.get("note", "")
        if word and not item.get("is_ad", False):
            results.append({
                "title": word.strip(),
                "url": f"https://s.weibo.com/weibo?q={word}",
                "source": "微博热搜",
            })
    return results


def fetch_hackernews():
    """Hacker News"""
    ids = _fetch("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not ids:
        return []
    results = []
    for sid in ids[:10]:
        item = _fetch(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
        if item and item.get("title"):
            results.append({
                "title": item["title"].strip(),
                "url": item.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                "source": "Hacker News",
            })
    return results


def fetch_baidu_hot():
    """百度热搜"""
    data = _fetch("https://top.baidu.com/board?tab=realtime")
    if not data:
        return []
    results = []
    # 百度热榜返回 HTML，从 JSON 数据中提取
    cards = data.get("data", {}).get("cards", [])
    for card in cards:
        for content in card.get("content", [])[:15]:
            word = content.get("word", "") or content.get("query", "")
            url = content.get("url", "") or content.get("appUrl", "")
            if word:
                results.append({
                    "title": word.strip(),
                    "url": url if url.startswith("http") else f"https://www.baidu.com/s?wd={word}",
                    "source": "百度热搜",
                })
    return results


def _fetch_daily_all():
    """拉取所有每日来源"""
    all_items = []
    fetchers = [
        ("weibo", fetch_weibo_hot),
        ("baidu", fetch_baidu_hot),
        ("hn", fetch_hackernews),
    ]
    for name, fn in fetchers:
        try:
            items = fn()
            print(f"  [{name}] {len(items)} 条")
            all_items.extend(items)
        except Exception as e:
            print(f"  [{name}] 失败: {e}")
    return deduplicate(all_items)


# ─── 主入口 ─────────────────────────────────────

def fetch_all_news(limit=15):
    """主入口：优先周刊，否则聚合每日来源"""
    print("  检查周刊更新...")
    weekly = fetch_weekly_if_new()
    if weekly:
        return weekly

    print("  聚合每日新闻...")
    items = _fetch_daily_all()
    if not items:
        print("  所有来源均失败！")
        return []
    return items[:limit]
