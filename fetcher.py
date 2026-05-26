"""新闻采集：从阮一峰《科技爱好者周刊》拉取最新一期"""
import re
import ssl
import time
from urllib.request import urlopen, Request

HEADERS = {"User-Agent": "DailyTechBriefing/1.0"}
REPO_RAW = "https://raw.githubusercontent.com/ruanyf/weekly/master"
MAX_RETRIES = 3
RETRY_DELAY = 2


def _fetch_text(url, retries=MAX_RETRIES):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    for attempt in range(retries):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=20, context=ctx) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"  [fetch] {url[:80]}... 失败: {e}")
                return None


def _find_latest_issue():
    """解析 README 找到最新一期"""
    readme = _fetch_text(f"{REPO_RAW}/README.md")
    if not readme:
        return None
    # 匹配第一个 issue 链接，如：第 397 期：[财富正在向 AI 集中](docs/issue-397.md)
    m = re.search(r'第\s*(\d+)\s*期[：:]\s*[^]]*\]\(([^)]+)\)', readme)
    if not m:
        return None
    issue_num = int(m.group(1))
    issue_path = m.group(2)
    issue_url = f"{REPO_RAW}/{issue_path}"
    return issue_num, issue_url


def _strip_markdown(text):
    """清洗 Markdown：去图片、去 HTML、保留纯文本"""
    # 去掉图片 ![alt](url)
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # 去掉链接 [text](url) 保留文字
    text = re.sub(r'\[([^\]]*)\]\([^)]+\)', r'\1', text)
    # 去掉 Markdown 标记（粗体斜体等）
    text = re.sub(r'\*{1,3}', '', text)
    # 去掉多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def fetch_all_news(limit=1):
    """主入口：拉取最新一期周刊"""
    result = _find_latest_issue()
    if not result:
        print("  [fetch] 未找到最新一期周刊")
        return []

    issue_num, issue_url = result
    print(f"  找到第 {issue_num} 期: {issue_url}")

    content = _fetch_text(issue_url)
    if not content:
        return []

    # 提取标题
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1) if title_match else f"第 {issue_num} 期"

    # 清洗内容
    body = _strip_markdown(content)
    # 去掉第一行标题（已单独提取）
    body = re.sub(r'^.*?\n', '', body, count=1).strip()
    # 截取前 8000 字（足够 AI 理解，控制 token 消耗）
    if len(body) > 8000:
        body = body[:8000] + "\n\n（内容过长已截断）"

    return [{
        "title": title,
        "url": f"https://github.com/ruanyf/weekly/blob/master/docs/issue-{issue_num}.md",
        "source": f"科技爱好者周刊 第{issue_num}期",
        "body": body,
    }]
