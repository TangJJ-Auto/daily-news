"""PushPlus 推送：发送到微信"""
import requests
from config import PUSHPLUS_TOKEN


def push(title, content):
    """
    通过 PushPlus 推送消息到微信。
    返回 (success, detail) — success 表示请求是否被 PushPlus 受理。
    """
    if not PUSHPLUS_TOKEN:
        print("[push] PUSHPLUS_TOKEN 未设置，跳过推送")
        return False, "TOKEN未设置"

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
        code = data.get("code")
        msg = data.get("msg", "")
        short_code = data.get("data", "")

        print(f"[push] code={code} msg={msg} shortCode={short_code}")

        if code == 200:
            print(f"[push] 请求已受理（异步发送中），可登录 pushplus.plus 查看发送记录")
            return True, f"shortCode={short_code}"
        else:
            print(f"[push] 请求失败: code={code} msg={msg}")
            return False, f"code={code} {msg}"

    except Exception as e:
        print(f"[push] 请求异常: {e}")
        return False, str(e)
