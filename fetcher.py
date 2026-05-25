"""新闻采集：从多个科技新闻源拉取热榜"""
import json
import ssl
import time
from difflib import SequenceMatcher
from urllib.request import urlopen, Request

HEADERS = {"User-Agent": "DailyTechBriefing/1.0"}
MAX_RETRIES = 3
RETRY_DELAY = 2


def _fetch_json(url, retries=MAX_RETRIES):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for attempt in range(retries):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=20, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"  [fetch] {url[:60]}... 失败: {e}")
                return None


def fetch_36kr():
    """36氪热榜"""
    data = _fetch_json("https://www.36kr.com/api/search-column/300024")
    if not data:
        return []
    items = data.get("data", {}).get("items", [])
    results = []
    for item in items[:10]:
        title = item.get("title", "") or item.get("post", {}).get("title", "")
        url = item.get("url", "") or f"https://36kr.com/p/{item.get('id', '')}"
        if title:
            results.append({"title": title.strip(), "url": url, "source": "36氪"})
    return results


def fetch_zhihu():
    """知乎热榜"""
    data = _fetch_json("https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20")
    if not data:
        return []
    results = []
    for item in data.get("data", [])[:10]:
        target = item.get("target", {})
        title = target.get("title", "")
        qid = target.get("id")
        if title:
            results.append({
                "title": title.strip(),
                "url": f"https://www.zhihu.com/question/{qid}" if qid else "",
                "source": "知乎",
            })
    return results


def fetch_hackernews():
    """Hacker News top stories"""
    ids = _fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not ids:
        return []
    results = []
    for story_id in ids[:10]:
        item = _fetch_json(
            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        )
        if item and item.get("title"):
            results.append({
                "title": item["title"].strip(),
                "url": item.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                "source": "Hacker News",
            })
    return results


def _title_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(items, threshold=0.6):
    """基于标题相似度去重，保留先出现的"""
    seen = []
    for item in items:
        if not any(
            _title_similarity(item["title"], s["title"]) > threshold for s in seen
        ):
            seen.append(item)
    return seen


def fetch_all_news(limit=15):
    """主入口：拉取全部新闻源，去重，返回 top N"""
    fetchers = [fetch_36kr, fetch_zhihu, fetch_hackernews]
    all_items = []
    for fetcher in fetchers:
        try:
            items = fetcher()
            all_items.extend(items)
        except Exception:
            continue

    all_items = deduplicate(all_items)
    return all_items[:limit]
