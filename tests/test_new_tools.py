"""New tools that match existing blog demand: PDF->JPG, HEIC->JPG, MP4->GIF."""
import io
import json
import os
import re
import zipfile

import pytest
from PIL import Image

import server
from blog_data import BLOG_ARTICLES
from conftest import assert_article_cta_or_redirect, make_pdf

NEW_TOOLS = ["pdf-to-jpg", "heic-to-jpg", "mp4-to-gif"]


def download(client, result):
    assert server.FILE_ID_RE.match(result["file_id"]), result
    r = client.get(f"/api/download/{result['file_id']}")
    assert r.status_code == 200
    return r.content


# ---------------- PDF -> JPG ----------------

def test_pdf_to_jpg_single_page_returns_jpg(client):
    r = client.post("/api/convert/pdf-to-jpg", files={"file": ("doc.pdf", make_pdf(1), "application/pdf")})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "doc.jpg"
    img = Image.open(io.BytesIO(download(client, res)))
    assert img.format == "JPEG"
    assert abs(img.width - 1275) <= 3 and abs(img.height - 1650) <= 3  # Letter @ 150 DPI


def test_pdf_to_jpg_multi_page_returns_zip(client):
    r = client.post("/api/convert/pdf-to-jpg", files={"file": ("report.pdf", make_pdf(3), "application/pdf")})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "report_jpg.zip"
    zf = zipfile.ZipFile(io.BytesIO(download(client, res)))
    assert zf.namelist() == ["report-page-1.jpg", "report-page-2.jpg", "report-page-3.jpg"]
    for n in zf.namelist():
        assert Image.open(io.BytesIO(zf.read(n))).format == "JPEG"


def test_pdf_to_jpg_page_cap(client):
    r = client.post("/api/convert/pdf-to-jpg",
                    files={"file": ("big.pdf", make_pdf(server.PDF_TO_JPG_MAX_PAGES + 1), "application/pdf")})
    assert r.status_code == 400
    assert str(server.PDF_TO_JPG_MAX_PAGES) in r.json()["detail"]


def test_pdf_to_jpg_rejects_garbage_and_cleans_up(client):
    before = set(os.listdir(server.TEMP_DIR))
    r = client.post("/api/convert/pdf-to-jpg", files={"file": ("x.pdf", b"not a pdf at all", "application/pdf")})
    assert r.status_code == 400
    assert set(os.listdir(server.TEMP_DIR)) <= before


def test_pdf_to_jpg_upload_cap(client):
    big = b"%PDF-1.4\n" + b"0" * (int(server.MAX_UPLOAD_MB * 1024 * 1024) + 2 * 1024 * 1024)
    r = client.post("/api/convert/pdf-to-jpg", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_zip_download_page_renders(client):
    res = client.post("/api/convert/pdf-to-jpg",
                      files={"file": ("a.pdf", make_pdf(2), "application/pdf")}).json()
    r = client.get(f"/download-page?file_id={res['file_id']}&filename={res['filename']}")
    assert r.status_code == 200 and "a_jpg.zip" in r.text


# ---------------- HEIC -> JPG ----------------

def test_heic_to_jpg(client):
    import pillow_heif
    pillow_heif.register_heif_opener()
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (200, 10, 10)).save(buf, format="HEIF")
    r = client.post("/api/convert/heic-to-jpg", files={"file": ("IMG_0001.HEIC", buf.getvalue(), "image/heic")})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "IMG_0001.jpg"
    img = Image.open(io.BytesIO(download(client, res)))
    assert img.format == "JPEG" and img.size == (64, 48)


def test_heic_to_jpg_rejects_garbage(client):
    r = client.post("/api/convert/heic-to-jpg", files={"file": ("x.heic", b"nope", "image/heic")})
    assert r.status_code == 400


# ---------------- MP4 -> GIF ----------------

@pytest.fixture(scope="module")
def tiny_mp4(tmp_path_factory):
    import subprocess
    if not server.FFMPEG_PATH:
        pytest.skip("ffmpeg not available")
    out = tmp_path_factory.mktemp("v") / "clip.mp4"
    subprocess.run([server.FFMPEG_PATH, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=320x240:rate=10:duration=2", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out.read_bytes()


def test_mp4_to_gif(client, tiny_mp4):
    r = client.post("/api/convert/mp4-to-gif", files={"file": ("clip.mp4", tiny_mp4, "video/mp4")})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "clip.gif"
    img = Image.open(io.BytesIO(download(client, res)))
    assert img.format == "GIF" and getattr(img, "n_frames", 1) > 1
    assert img.width <= server.GIF_MAX_WIDTH


def test_mp4_to_gif_rejects_garbage(client):
    r = client.post("/api/convert/mp4-to-gif", files={"file": ("x.mp4", b"nope", "video/mp4")})
    assert r.status_code == 400


# ---------------- SEO parity for the new tool pages ----------------

@pytest.mark.parametrize("slug", NEW_TOOLS)
def test_new_tool_page_seo_parity(client, slug):
    r = client.get(f"/{slug}")
    assert r.status_code == 200
    html = r.text
    types = {json.loads(b.replace("<\\/", "</")).get("@type")
             for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)}
    assert {"WebApplication", "FAQPage", "BreadcrumbList"} <= types
    assert "<details" in html and "Related" in html
    assert f"{server.SITE_URL}/{slug}</loc>" in client.get("/sitemap.xml").text
    assert f"{server.SITE_URL}/{slug})" in client.get("/llms.txt").text
    assert f'href="/{slug}"' in client.get("/").text


def test_llms_txt_counts_match_reality(client):
    body = client.get("/llms.txt").text
    assert f"{len(server.TOOLS_CONFIG)} dedicated conversion tools" in body
    assert f"{len(BLOG_ARTICLES)} in-depth conversion guides" in body


@pytest.mark.parametrize("article,tool", [
    ("how-to-convert-pdf-to-jpg", "/pdf-to-jpg"),
    ("how-to-convert-heic-to-jpg", "/heic-to-jpg"),
    ("what-is-heic-format", "/heic-to-jpg"),
    ("how-to-convert-mp4-to-gif", "/mp4-to-gif"),
])
def test_blog_ctas_point_to_matching_tool(client, article, tool):
    assert_article_cta_or_redirect(client, article, tool)


def test_pdf_to_jpg_huge_page_is_downscaled_not_oom(client):
    buf = io.BytesIO()
    # 200 px at 1 DPI -> a 14400 x 14400 pt page (PDF max); 150 DPI would be 30000 x 30000 px.
    Image.new("RGB", (200, 200), "white").save(buf, "PDF", resolution=1)
    r = client.post("/api/convert/pdf-to-jpg", files={"file": ("huge.pdf", buf.getvalue(), "application/pdf")})
    assert r.status_code == 200, r.text
    img = Image.open(io.BytesIO(download(client, r.json())))
    assert img.width * img.height <= server.PDF_TO_JPG_MAX_PIXELS


@pytest.fixture(scope="module")
def portrait_mp4(tmp_path_factory):
    import subprocess
    if not server.FFMPEG_PATH:
        pytest.skip("ffmpeg not available")
    out = tmp_path_factory.mktemp("p") / "tall.mp4"
    subprocess.run([server.FFMPEG_PATH, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=240x1280:rate=10:duration=1", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out.read_bytes()


def test_mp4_to_gif_caps_height_for_portrait_video(client, portrait_mp4):
    r = client.post("/api/convert/mp4-to-gif", files={"file": ("tall.mp4", portrait_mp4, "video/mp4")})
    assert r.status_code == 200, r.text
    img = Image.open(io.BytesIO(download(client, r.json())))
    assert img.height <= server.GIF_MAX_HEIGHT and img.width <= server.GIF_MAX_WIDTH
