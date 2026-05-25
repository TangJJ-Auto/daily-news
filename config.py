import os

# PushPlus — 注册 pushplus.net 获取 token
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")

# DeepSeek API — platform.deepseek.com 获取 key
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 送入 AI 摘要的最大新闻条数
MAX_NEWS_ITEMS = 15

# AI 摘要输出条数
SUMMARY_COUNT = 6
