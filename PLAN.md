# 每日科技速递 — 实现计划

> **Goal:** 每天早上 8:30 通过 GitHub Actions 自动抓取科技新闻，DeepSeek 故事化重写后 PushPlus 推送到微信

**Architecture:** Python 脚本分为 fetcher/summarizer/pusher 三个独立模块，main 脚本串联。GitHub Actions 定时触发执行。

**Tech Stack:** Python 3.x + requests + openai SDK, DeepSeek API, PushPlus, GitHub Actions

---

### Task 1: 项目骨架和依赖

**Files:**
- Create: `projects/daily-news/requirements.txt`
- Create: `projects/daily-news/config.py`

- [ ] **Step 1: 创建 requirements.txt**

```
requests>=2.28.0
openai>=1.0.0
```

- [ ] **Step 2: 创建 config.py**

```python
import os

# PushPlus
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")

# DeepSeek API (兼容 OpenAI SDK)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 新闻采集数量
MAX_NEWS_ITEMS = 15

# AI 摘要输出数量
SUMMARY_COUNT = 6
```

- [ ] **Step 3: 验证依赖安装**

Run: `pip install -r requirements.txt`
Expected: 无报错

---

### Task 2: 新闻采集模块

**Files:**
- Create: `projects/daily-news/fetcher.py`

- [ ] **Step 1: 实现 fetcher.py**

```python
"""新闻采集：从多个科技新闻源拉取热榜"""
import json
from difflib import SequenceMatcher
from urllib.request import urlopen, Request

HEADERS = {"User-Agent": "DailyTechBriefing/1.0"}

SOURCES = [
    {
        "name": "36氪",
        "url": "https://www.36kr.com/api/search-column/300024",
    },
    {
        "name": "知乎热榜",
        "url": "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20",
    },
    {
        "name": "Hacker News",
        "url": "https://hacker-news.firebaseio.com/v0/topstories.json",
    },
]


def _fetch_json(url):
    """通用 JSON 抓取，失败返回 None"""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def fetch_36kr():
    """36氪热榜，返回 [{title, url, source}]"""
    data = _fetch_json(SOURCES[0]["url"])
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
    """知乎热榜，返回 [{title, url, source}]"""
    data = _fetch_json(SOURCES[1]["url"])
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
    """Hacker News top stories，返回 [{title, url, source}]"""
    ids = _fetch_json(SOURCES[2]["url"])
    if not ids:
        return []
    results = []
    for story_id in ids[:10]:
        url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        item = _fetch_json(url)
        if item and item.get("title"):
            results.append({
                "title": item["title"].strip(),
                "url": item.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                "source": "Hacker News",
            })
    return results


def _title_similarity(a, b):
    """两个标题的相似度 0-1"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(items, threshold=0.6):
    """基于标题相似度去重，保留先出现的"""
    seen = []
    for item in items:
        if not any(_title_similarity(item["title"], s["title"]) > threshold for s in seen):
            seen.append(item)
    return seen


def fetch_all_news(limit=15):
    """主入口：拉取全部新闻源，去重，返回 top N"""
    all_items = []
    for fetcher in [fetch_36kr, fetch_zhihu, fetch_hackernews]:
        try:
            items = fetcher()
            all_items.extend(items)
        except Exception:
            continue

    all_items = deduplicate(all_items)
    return all_items[:limit]
```

- [ ] **Step 2: 测试采集模块**

Run: `cd projects/daily-news && python -c "from fetcher import fetch_all_news; items = fetch_all_news(); print(f'Fetched {len(items)} items'); [print(f'  [{i[\"source\"]}] {i[\"title\"]}') for i in items]"`

Expected: 输出采集到的新闻条数和标题

---

### Task 3: AI 摘要模块

**Files:**
- Create: `projects/daily-news/summarizer.py`

- [ ] **Step 1: 实现 summarizer.py**

```python
"""AI 摘要：调用 DeepSeek API，故事化重写新闻"""
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MAX_NEWS_ITEMS, SUMMARY_COUNT

SYSTEM_PROMPT = """你是科技新闻主编，给一个程序员朋友写每日科技速递。

要求：
1. 每条新闻一小段，讲清楚三件事：发生了什么 → 为什么重要 → 跟你有啥关系
2. 像朋友聊天一样自然，可以调侃但不下结论。去套话、补背景、有态度
3. 只选最值得关注的 {} 条，宁缺毋滥
4. 每条以数字序号开头，格式：1. **加粗标题**
5. 最后加一行 "---" 和一句今天的总结或吐槽（可选）

输入是各平台热榜标题，你可能需要结合自己的知识判断每条新闻的真实背景和重要性。""".format(SUMMARY_COUNT)


def summarize(news_items):
    """
    将新闻列表发送给 DeepSeek 做故事化摘要。
    成功返回 (markdown_text, None)，失败返回 (fallback_text, error_msg)
    """
    if not news_items:
        return "今天没什么大新闻，摸鱼快乐。", None

    news_text = "\n".join(
        f"{i+1}. [{item['source']}] {item['title']}"
        for i, item in enumerate(news_items[:MAX_NEWS_ITEMS])
    )

    user_prompt = f"以下是今日科技热榜标题，请按你的风格写出今日速递：\n\n{news_text}"

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=2048,
        )
        return response.choices[0].message.content.strip(), None

    except Exception as e:
        # 降级：返回纯标题列表
        fallback = "**今日科技速递**（AI 摘要服务暂时不可用，先看标题吧）\n\n"
        for i, item in enumerate(news_items[:SUMMARY_COUNT]):
            source = item["source"]
            title = item["title"]
            url = item["url"]
            fallback += f"{i+1}. [{title}]({url}) — {source}\n"
        return fallback, str(e)
```

- [ ] **Step 2: 测试摘要模块（需要 DEEPSEEK_API_KEY）**

Run: `cd projects/daily-news && set DEEPSEEK_API_KEY=your_key && python -c "from fetcher import fetch_all_news; from summarizer import summarize; items = fetch_all_news(); text, err = summarize(items); print(text); print('ERR:', err)"`

Expected: 输出故事化新闻文本（或降级标题列表）

---

### Task 4: 推送模块

**Files:**
- Create: `projects/daily-news/pusher.py`

- [ ] **Step 1: 实现 pusher.py**

```python
"""PushPlus 推送：发送到微信"""
import requests
from config import PUSHPLUS_TOKEN


def push(title, content):
    """
    通过 PushPlus 推送消息到微信。
    成功返回 True，失败返回 False。
    """
    if not PUSHPLUS_TOKEN:
        print("[push] PUSHPLUS_TOKEN 未设置，跳过推送")
        return False

    try:
        resp = requests.post(
            "https://www.pushplus.plus/send",
            json={
                "token": PUSHPLUS_TOKEN,
                "title": title,
                "content": content,
                "template": "markdown",
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("code") == 200:
            print("[push] 推送成功")
            return True
        else:
            print(f"[push] 推送失败: {data.get('msg', 'unknown')}")
            return False
    except Exception as e:
        print(f"[push] 推送异常: {e}")
        return False
```

---

### Task 5: 主入口

**Files:**
- Create: `projects/daily-news/news_briefing.py`

- [ ] **Step 1: 实现 news_briefing.py**

```python
"""每日科技速递 — 主入口"""
import sys
from datetime import datetime
from fetcher import fetch_all_news
from summarizer import summarize
from pusher import push


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{today}] 开始生成每日科技速递...")

    # 1. 采集新闻
    print("[1/3] 采集新闻...")
    news_items = fetch_all_news()
    print(f"  获取到 {len(news_items)} 条新闻")
    if not news_items:
        print("[FAIL] 未获取到任何新闻，退出")
        sys.exit(1)

    # 2. AI 摘要
    print("[2/3] AI 摘要生成中...")
    summary_text, error = summarize(news_items)
    if error:
        print(f"  降级模式: {error}")
    print(f"  生成 {len(summary_text)} 字符")

    # 3. 推送微信
    print("[3/3] 推送到微信...")
    title = f"科技速递 · {today}"
    success = push(title, summary_text)
    if success:
        print("[DONE] 推送成功!")
    else:
        print("[FAIL] 推送失败，内容如下:\n")
        print(summary_text)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 本地全流程测试**

Run: `cd projects/daily-news && set PUSHPLUS_TOKEN=your_token && set DEEPSEEK_API_KEY=your_key && python news_briefing.py`

Expected: 完整的采集 → 摘要 → 推送流程，微信收到消息

---

### Task 6: GitHub Actions 定时调度

**Files:**
- Create: `projects/daily-news/.github/workflows/daily.yml`

- [ ] **Step 1: 创建 workflow 文件**

```yaml
name: Daily Tech Briefing

on:
  schedule:
    - cron: "30 0 * * *"   # UTC 0:30 = CST 8:30
  workflow_dispatch:        # 允许手动触发测试

jobs:
  briefing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run briefing
        env:
          PUSHPLUS_TOKEN: ${{ secrets.PUSHPLUS_TOKEN }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: python news_briefing.py
```

- [ ] **Step 2: 在 GitHub 仓库设置 Secrets**
  - 打开仓库 Settings → Secrets and variables → Actions
  - 添加 `PUSHPLUS_TOKEN`
  - 添加 `DEEPSEEK_API_KEY`

- [ ] **Step 3: 手动触发测试**

仓库页面 → Actions → Daily Tech Briefing → Run workflow → 确认收到微信推送
