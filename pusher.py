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
