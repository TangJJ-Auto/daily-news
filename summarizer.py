"""AI 摘要：调用 DeepSeek API，从周刊内容提炼故事化速递"""
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MAX_NEWS_ITEMS, SUMMARY_COUNT

SYSTEM_PROMPT = """你是科技新闻主编，给一个程序员朋友写每日科技速递。

你的原材料是阮一峰《科技爱好者周刊》的完整文章。从中精选 {count} 条最值得关注的科技内容，按你的风格重写。

要求：
1. 每条一小段，讲清楚三件事：发生了什么 → 为什么重要 → 跟你有啥关系
2. 像朋友聊天一样自然，可以调侃但不下结论。去套话、补背景、有态度
3. 只选最值得关注的 {count} 条，宁缺毋滥
4. 每条以数字序号开头，格式：1. **加粗标题**
5. 最后加一行 "---" 和一句总结或吐槽""".format(count=SUMMARY_COUNT)


def summarize(news_items):
    """
    将周刊内容发送给 DeepSeek 做故事化摘要。
    成功返回 (markdown_text, None)，失败返回 (fallback_text, error_msg)

    news_items 格式：[{title, url, source, body}]
    """
    if not news_items:
        return "今天没什么大新闻，摸鱼快乐。", None

    item = news_items[0]
    source_name = item["source"]
    article_body = item.get("body", item.get("title", ""))

    user_prompt = (
        f"来源：{source_name}\n"
        f"原文标题：{item['title']}\n\n"
        f"以下是本期完整内容，请从中挑选最值得关注的 {SUMMARY_COUNT} 条，按你的风格写出速递：\n\n"
        f"{article_body}"
    )

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
        fallback = (
            f"**{source_name}**\n"
            f"[{item['title']}]({item['url']})\n\n"
            "AI 摘要服务暂时不可用，可直接阅读原文。"
        )
        return fallback, str(e)
