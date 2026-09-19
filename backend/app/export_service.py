"""Converts fetched WeChat article payloads into a downloadable backup ZIP."""

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from markdownify import markdownify as html_to_md

IMG_SRC_RE = re.compile(r'<img[^>]+(?:data-src|src)="([^"]+)"')


def sanitize_filename(name: str, max_len: int = 80) -> str:
    name = re.sub(r'[\\/:*?"<>|\n\r\t]', "_", name).strip()
    return name[:max_len] or "untitled"


async def _download_image(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        resp = await client.get(url, timeout=15)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None


async def _localize_images(
    html: str, image_dir_name: str, client: httpx.AsyncClient, work_dir: Path
) -> str:
    urls = list(dict.fromkeys(IMG_SRC_RE.findall(html)))
    if not urls:
        return html
    img_dir = work_dir / "images" / image_dir_name
    for i, url in enumerate(urls):
        data = await _download_image(client, url)
        if data is None:
            continue
        ext = Path(urlparse(url).path).suffix
        if not ext or len(ext) > 5:
            ext = ".jpg"
        img_dir.mkdir(parents=True, exist_ok=True)
        (img_dir / f"{i + 1}{ext}").write_bytes(data)
        html = html.replace(url, f"images/{image_dir_name}/{i + 1}{ext}")
    return html


async def export_articles(
    publish_items: list[dict],
    formats: set[str],
    with_images: bool,
    work_dir: Path,
) -> Path:
    (work_dir / "raw").mkdir(parents=True, exist_ok=True)
    if "html" in formats:
        (work_dir / "html").mkdir(parents=True, exist_ok=True)
    if "markdown" in formats:
        (work_dir / "articles").mkdir(parents=True, exist_ok=True)

    manifest = []

    async with httpx.AsyncClient() as client:
        for pub in publish_items:
            article_id = pub.get("article_id", "unknown")
            update_time = pub.get("update_time", 0)
            date = datetime.fromtimestamp(update_time) if update_time else datetime.now()

            (work_dir / "raw" / f"{article_id}.json").write_text(
                json.dumps(pub, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            for idx, item in enumerate(pub.get("content", {}).get("news_item", [])):
                title = item.get("title", "untitled")
                content_html = item.get("content", "")
                slug = sanitize_filename(title)
                image_dir_name = f"{article_id}-{idx}"

                if with_images:
                    content_html = await _localize_images(content_html, image_dir_name, client, work_dir)

                if "html" in formats:
                    (work_dir / "html" / f"{article_id}-{idx}-{slug}.html").write_text(
                        content_html, encoding="utf-8"
                    )

                if "markdown" in formats:
                    year_dir = work_dir / "articles" / str(date.year)
                    year_dir.mkdir(parents=True, exist_ok=True)
                    front_matter = (
                        f"---\ntitle: {title}\ndate: {date.isoformat()}\n"
                        f"url: {item.get('url', '')}\narticle_id: {article_id}\n---\n\n"
                    )
                    md_body = html_to_md(content_html, heading_style="ATX")
                    (year_dir / f"{date.strftime('%Y-%m-%d')}-{slug}.md").write_text(
                        front_matter + md_body, encoding="utf-8"
                    )

                manifest.append(
                    {
                        "article_id": article_id,
                        "index": idx,
                        "title": title,
                        "url": item.get("url", ""),
                        "publish_time": date.isoformat(),
                    }
                )

    if "json" in formats:
        (work_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    zip_path = work_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in work_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(work_dir))
    return zip_path
