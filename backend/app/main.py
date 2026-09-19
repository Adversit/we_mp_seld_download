import shutil
import tempfile
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from .export_service import export_articles
from .wechat_client import WeChatAPIError, WeChatOfficialClient

app = FastAPI(title="WeChat Article Backup")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Credentials(BaseModel):
    app_id: str
    app_secret: str


class ExportRequest(Credentials):
    formats: list[str] = ["markdown", "html", "json"]
    with_images: bool = True


@app.get("/api/server-ip")
async def server_ip():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get("https://api.ipify.org?format=json")
    return resp.json()


@app.post("/api/account/verify")
async def verify_account(creds: Credentials):
    client = WeChatOfficialClient(creds.app_id, creds.app_secret)
    try:
        token = await client.get_stable_token()
        data = await client.list_published(token, offset=0, count=1)
    except WeChatAPIError as e:
        raise HTTPException(status_code=400, detail={"errcode": e.errcode, "errmsg": e.errmsg})
    return {"ok": True, "total_count": data.get("total_count", 0)}


@app.post("/api/articles/scan")
async def scan_articles(creds: Credentials):
    client = WeChatOfficialClient(creds.app_id, creds.app_secret)
    try:
        token = await client.get_stable_token()
        publish_items = await client.list_all_published(token)
    except WeChatAPIError as e:
        raise HTTPException(status_code=400, detail={"errcode": e.errcode, "errmsg": e.errmsg})

    summary = [
        {
            "article_id": pub.get("article_id"),
            "index": idx,
            "title": item.get("title"),
            "url": item.get("url"),
            "update_time": pub.get("update_time"),
        }
        for pub in publish_items
        for idx, item in enumerate(pub.get("content", {}).get("news_item", []))
    ]
    return {"total": len(summary), "articles": summary}


@app.post("/api/export")
async def export(req: ExportRequest):
    client = WeChatOfficialClient(req.app_id, req.app_secret)
    try:
        token = await client.get_stable_token()
        publish_items = await client.list_all_published(token)
    except WeChatAPIError as e:
        raise HTTPException(status_code=400, detail={"errcode": e.errcode, "errmsg": e.errmsg})

    work_dir = Path(tempfile.mkdtemp()) / f"backup-{uuid.uuid4().hex[:8]}"
    zip_path = await export_articles(publish_items, set(req.formats), req.with_images, work_dir)
    cleanup = BackgroundTask(shutil.rmtree, work_dir.parent, ignore_errors=True)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_path.name,
        background=cleanup,
    )


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
