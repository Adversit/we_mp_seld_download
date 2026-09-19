from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.wechat_client import WeChatAPIError

client = TestClient(app)

FAKE_PUBLISH_ITEM = {
    "article_id": "ART123",
    "update_time": 1700000000,
    "content": {
        "news_item": [
            {"title": "标题一", "content": "<p>内容</p>", "url": "https://mp.weixin.qq.com/s/aaa"}
        ]
    },
}


def test_verify_account_success():
    with patch("app.main.WeChatOfficialClient") as MockClient:
        instance = MockClient.return_value
        instance.get_stable_token = AsyncMock(return_value="token123")
        instance.list_published = AsyncMock(return_value={"total_count": 5, "item": []})

        resp = client.post("/api/account/verify", json={"app_id": "wx1", "app_secret": "secret1"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "total_count": 5}


def test_verify_account_wechat_error_maps_to_400():
    with patch("app.main.WeChatOfficialClient") as MockClient:
        instance = MockClient.return_value
        instance.get_stable_token = AsyncMock(side_effect=WeChatAPIError(40013, "invalid appid"))

        resp = client.post("/api/account/verify", json={"app_id": "bad", "app_secret": "bad"})

    assert resp.status_code == 400
    assert resp.json()["detail"] == {"errcode": 40013, "errmsg": "invalid appid"}


def test_scan_articles_flattens_news_items():
    with patch("app.main.WeChatOfficialClient") as MockClient:
        instance = MockClient.return_value
        instance.get_stable_token = AsyncMock(return_value="token123")
        instance.list_all_published = AsyncMock(return_value=[FAKE_PUBLISH_ITEM])

        resp = client.post("/api/articles/scan", json={"app_id": "wx1", "app_secret": "secret1"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["articles"][0]["title"] == "标题一"


def test_export_returns_zip_file():
    with patch("app.main.WeChatOfficialClient") as MockClient:
        instance = MockClient.return_value
        instance.get_stable_token = AsyncMock(return_value="token123")
        instance.list_all_published = AsyncMock(return_value=[FAKE_PUBLISH_ITEM])

        resp = client.post(
            "/api/export",
            json={
                "app_id": "wx1",
                "app_secret": "secret1",
                "formats": ["markdown", "json"],
                "with_images": False,
            },
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert len(resp.content) > 0
