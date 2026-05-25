"""AI 摘要：调用 DeepSeek API，故事化重写新闻"""
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MAX_NEWS_ITEMS, SUMMARY_COUNT

SYSTEM_PROMPT = """你是科技新闻主编，给一个程序员朋友写每日科技速递。

要求：
1. 每条新闻一小段，讲清楚三件事：发生了什么 → 为什么重要 → 跟你有啥关系
2. 像朋友聊天一样自然，可以调侃但不下结论。去套话、补背景、有态度
3. 只选最值得关注的 {count} 条，宁缺毋滥
4. 每条以数字序号开头，格式：1. **加粗标题**
5. 最后加一行 "---" 和一句今天的总结或吐槽""".format(count=SUMMARY_COUNT)


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
        fallback = "**今日科技速递**（AI 摘要服务暂时不可用）\n\n"
        for i, item in enumerate(news_items[:SUMMARY_COUNT]):
            fallback += f"{i+1}. [{item['title']}]({item['url']}) — {item['source']}\n"
        return fallback, str(e)
