# 每日科技速递 — 设计文档

## 概述

每天早上 8:30 自动抓取科技新闻，用大模型故事化重写，通过 PushPlus 推送到个人微信。

## 核心约束

- **用户网络环境**：学生，依赖手机热点，电脑多数时间断网
- **关键决策**：使用 GitHub Actions 云端执行，不依赖用户电脑在线
- **推送要求**：手机微信接收，PushPlus 免费额度满足日推一条

## 架构

```
GitHub Actions (schedule: 8:30 CST)
    │
    ▼
Python 脚本 (news_briefing.py)
    ├── ① fetch: 从多个科技新闻源拉取热榜
    ├── ② filter: 去重、去非科技内容、按热度排序
    ├── ③ summarize: 调用 DeepSeek API，故事化重写
    └── ④ push: PushPlus API → 用户微信
```

## 模块设计

### 1. 新闻采集 (fetcher.py)

- 数据源：36氪热榜 API、知乎热榜（科技话题）、Hacker News API
- 每个源返回 `[{title, url, source, rank}]`
- 合并去重：基于 URL 和标题相似度（difflib）
- 保留 top 15 送入 AI 加工

### 2. AI 摘要 (summarizer.py)

- 模型：DeepSeek Chat API（便宜且中文效果好）
- 输入：15 条原始标题 + 摘要
- 输出：5-8 条故事化新闻，每条 2-4 句
- Prompt 风格：
  - 三条核心要求：发生了什么 → 为什么重要 → 跟你有啥关系
  - 语调：朋友聊天，不端不水，可以调侃但不下结论
  - 去套话、补背景、有态度
- 降级：API 调用失败时，退化为纯标题列表推送

### 3. 推送 (pusher.py)

- 服务：PushPlus (pushplus.net)
- API：POST 请求，token + title + content
- 格式：Markdown，微信卡片展示

### 4. 调度 (GitHub Actions)

```yaml
on:
  schedule:
    - cron: "30 0 * * *"  # UTC 0:30 = CST 8:30
```

- 执行：workflow 每天到点自动运行
- Secrets：PUSHPLUS_TOKEN、DEEPSEEK_API_KEY 存在 GitHub Secrets
- 失败通知：workflow 失败时 GitHub 会发邮件提醒

## 数据流

```
新闻源 API (free)
    → 原始标题列表
    → 去重 + 排序
    → DeepSeek API (付费, ~0.1元/天)
    → 故事化文本
    → PushPlus API (free)
    → 微信消息卡片
```

## 项目结构

```
daily-news/
├── news_briefing.py      # 主入口
├── fetcher.py            # 新闻采集
├── summarizer.py         # AI 摘要
├── pusher.py             # 微信推送
├── requirements.txt      # requests, openai
└── .github/workflows/
    └── daily.yml         # GitHub Actions 定时触发
```

## 风险 & 降级

| 风险 | 降级策略 |
|------|----------|
| 新闻源 API 挂了 | 跳过该源，用剩下的继续 |
| DeepSeek API 失败 | 退化为原始标题列表推送 |
| PushPlus 推送失败 | 日志记录，下次 workflow 重试 |
| 定时延迟（GitHub 排队） | 可接受，几分钟误差不关键 |
