import json
import zipfile

import pytest

from app.export_service import export_articles, sanitize_filename


def test_sanitize_filename_strips_illegal_chars():
    assert sanitize_filename('a/b:c*d?"e<f>g|h') == "a_b_c_d__e_f_g_h"


def test_sanitize_filename_empty_falls_back():
    assert sanitize_filename("   ") == "untitled"


FAKE_PUBLISH_ITEM = {
    "article_id": "ART123",
    "update_time": 1700000000,
    "content": {
        "news_item": [
            {
                "title": "测试文章标题",
                "content": "<p>正文内容 <b>加粗</b></p>",
                "url": "https://mp.weixin.qq.com/s/xxxx",
            }
        ]
    },
}


@pytest.mark.asyncio
async def test_export_articles_creates_expected_files(tmp_path):
    work_dir = tmp_path / "backup-test"
    zip_path = await export_articles(
        [FAKE_PUBLISH_ITEM],
        formats={"markdown", "html", "json"},
        with_images=False,
        work_dir=work_dir,
    )

    assert zip_path.exists()
    assert (work_dir / "raw" / "ART123.json").exists()
    assert (work_dir / "manifest.json").exists()

    md_files = list((work_dir / "articles" / "2023").glob("*.md"))
    assert len(md_files) == 1
    assert "测试文章标题" in md_files[0].read_text(encoding="utf-8")
    assert "加粗" in md_files[0].read_text(encoding="utf-8")

    html_files = list((work_dir / "html").glob("*.html"))
    assert len(html_files) == 1

    manifest = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest[0]["article_id"] == "ART123"
    assert manifest[0]["title"] == "测试文章标题"

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert any(name.endswith(".md") for name in names)
        assert any(name.endswith(".html") for name in names)
        assert "manifest.json" in names


@pytest.mark.asyncio
async def test_export_articles_respects_format_selection(tmp_path):
    work_dir = tmp_path / "backup-md-only"
    await export_articles(
        [FAKE_PUBLISH_ITEM],
        formats={"markdown"},
        with_images=False,
        work_dir=work_dir,
    )

    assert not (work_dir / "html").exists()
    assert not (work_dir / "manifest.json").exists()
    assert list((work_dir / "articles" / "2023").glob("*.md"))
