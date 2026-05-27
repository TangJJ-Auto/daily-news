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
    ok, detail = push(title, summary_text)
    if ok:
        print(f"[DONE] 请求受理: {detail}")
    else:
        print(f"[FAIL] 推送失败: {detail}")
        print(summary_text[:500])
        sys.exit(1)


if __name__ == "__main__":
    main()
