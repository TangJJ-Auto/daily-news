"""AI 摘要：多源新闻个性化重写，针对唐家杰"""
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, SUMMARY_COUNT

SYSTEM_PROMPT = f"""你是唐家杰的私人新闻秘书。他是一名20岁的自动化专业大学生、INFJ-T天蝎座，正在学习编程和AI。

你的任务：从今天的新闻素材中，精选 {SUMMARY_COUNT} 条对他最有价值的资讯，按他的口味重写。

选材原则（按优先级）：
1. 自动化/机器人/AI/编程相关 — 和他的专业直接相关
2. 科技行业大事件 — 影响他未来就业和方向选择
3. 国家大事/政策变化 — 影响大环境
4. 对大学生有用的信息 — 学习资源、职业建议、竞赛机会等

写作风格：
- 每条一小段，讲清楚：发生了什么 → 为什么重要 → 跟唐家杰有什么关系/他该怎么看
- 像学长跟学弟聊天，不端着，可以调侃但真诚
- 如果某条新闻跟自动化专业能扯上关系，一定要点出来
- 去套话、补背景、有态度，不要新闻联播腔
- 结尾加一句针对他的今日提醒或建议

格式：
1. **加粗标题**
   正文……
---
今日唐家杰建议：……

注意：如果某条明显是广告、八卦、或者跟他的世界毫无关系，直接跳过。宁缺毋滥。"""


def summarize(news_items):
    """
    将新闻发送给 DeepSeek 做个性化摘要。
    成功返回 (markdown_text, None)，失败返回 (fallback_text, error_msg)

    news_items 可以是周刊格式 [{title, url, source, body}] 或热榜格式 [{title, url, source}]
    """
    if not news_items:
        return "今天没什么重要新闻，建议唐家杰趁这个空档刷两道 LeetCode。", None

    # 判断是周刊还是热榜格式
    if "body" in news_items[0] and news_items[0]["body"]:
        item = news_items[0]
        source_label = item["source"]
        news_text = f"来源：{source_label}\n标题：{item['title']}\n\n{item['body'][:8000]}"
    else:
        news_text = "以下是今天各平台热榜，请根据你的知识判断每条新闻的真实背景：\n\n"
        for i, item in enumerate(news_items):
            news_text += f"{i+1}. [{item['source']}] {item['title']}\n"

    user_prompt = f"{news_text}\n\n请按你的风格，为唐家杰精选 {SUMMARY_COUNT} 条最有价值的今日资讯。"

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
        fallback = "**今日速递**（AI 暂不可用，以下是原始资讯）\n\n"
        if "body" in news_items[0] and news_items[0]["body"]:
            fallback += f"[{news_items[0]['title']}]({news_items[0]['url']})"
        else:
            for i, item in enumerate(news_items[:SUMMARY_COUNT]):
                fallback += f"{i+1}. [{item['title']}]({item['url']}) — {item['source']}\n"
        return fallback, str(e)
