"""Minimal client for the official WeChat Official Account (公众号) API.

Only uses documented endpoints: stable_token, freepublish/batchget,
freepublish/getarticle. No unofficial/back-channel endpoints.
"""

import httpx

WECHAT_API_BASE = "https://api.weixin.qq.com/cgi-bin"


class WeChatAPIError(Exception):
    def __init__(self, errcode: int, errmsg: str):
        self.errcode = errcode
        self.errmsg = errmsg
        super().__init__(f"{errcode}: {errmsg}")


class WeChatOfficialClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret

    async def get_stable_token(self) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{WECHAT_API_BASE}/stable_token",
                json={
                    "grant_type": "client_credential",
                    "appid": self.app_id,
                    "secret": self.app_secret,
                },
            )
        data = resp.json()
        if "access_token" not in data:
            raise WeChatAPIError(data.get("errcode", -1), data.get("errmsg", "unknown error"))
        return data["access_token"]

    async def list_published(self, access_token: str, offset: int = 0, count: int = 20) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{WECHAT_API_BASE}/freepublish/batchget",
                params={"access_token": access_token},
                json={"offset": offset, "count": count, "no_content": 0},
            )
        data = resp.json()
        if data.get("errcode"):
            raise WeChatAPIError(data["errcode"], data.get("errmsg", "unknown error"))
        return data

    async def list_all_published(self, access_token: str) -> list[dict]:
        articles: list[dict] = []
        offset = 0
        count = 20
        while True:
            data = await self.list_published(access_token, offset, count)
            items = data.get("item", [])
            articles.extend(items)
            if len(items) < count:
                break
            offset += count
        return articles
