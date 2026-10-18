"""v1.3: AI Background Remover (browser-side), QR Code Generator, GIF to MP4, 150/150 affiliate
articles, PNG social-share card."""
import io
import json
import os
import re
import shutil
import subprocess

import pytest
from PIL import Image

import server
from blog_data import BLOG_ARTICLES
from conftest import sitemap_paths

V13_TOOLS = ["remove-background", "qr-code-generator", "gif-to-mp4"]


def download(client, result):
    assert server.FILE_ID_RE.match(result["file_id"]), result
    r = client.get(f"/api/download/{result['file_id']}")
    assert r.status_code == 200
    return r.content


def jsonld(html):
    return [json.loads(b.replace("<\\/", "</"))
            for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


# ---------------- SEO parity ----------------

@pytest.mark.parametrize("slug", V13_TOOLS)
def test_v13_tool_page_seo(client, slug):
    tool = server.TOOLS_CONFIG[slug]
    html = client.get(f"/{slug}").text
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    assert "– Convert" not in title or slug == "gif-to-mp4", title
    assert "PureFileConverter" in title and len(title) <= 70, title
    desc = re.search(r'<meta name="description" content="(.*?)">', html).group(1)
    assert 70 <= len(desc) <= 165, (len(desc), desc)
    assert tool["intro"] in html
    blocks = jsonld(html)
    assert {"WebApplication", "FAQPage", "BreadcrumbList"} <= {b["@type"] for b in blocks}
    faq = next(b for b in blocks if b["@type"] == "FAQPage")
    visible = re.findall(r"<summary[^>]*>(.*?)</summary>", html)
    assert [q["name"] for q in faq["mainEntity"]] == visible   # schema matches the visible FAQ
    assert f"{server.SITE_URL}/{slug}</loc>" in client.get("/sitemap.xml").text
    assert f"{server.SITE_URL}/{slug})" in client.get("/llms.txt").text
    assert f'href="/{slug}"' in client.get("/").text
    assert "Related" in html and f'<link rel="canonical" href="{server.SITE_URL}/{slug}">' in html


def test_tool_count_and_sitemap():
    assert len(server.TOOLS_CONFIG) == 22


def test_sitemap_has_178_direct_urls(client):
    assert len(sitemap_paths(client)) == 178


def test_browser_tools_do_not_claim_server_upload(client):
    for slug in ["remove-background", "qr-code-generator"]:
        html = client.get(f"/{slug}").text
        assert "converted on our server" not in html, slug
        assert "maximum upload size" not in html, slug


def test_homepage_org_knows_new_tools(client):
    org = next(b for b in jsonld(client.get("/").text) if b["@type"] == "Organization")
    assert "AI background removal" in org["knowsAbout"] and "QR code generation" in org["knowsAbout"]


# ---------------- Remove Background (client-side) ----------------

def test_remove_background_page_wires_worker(client):
    html = client.get("/remove-background").text
    assert "/static/bg-remove-worker.js" in html
    assert "never uploaded" in html
    assert 'id="dropzone"' in html and 'id="bgDownload"' in html


def test_remove_background_worker_uses_permissive_stack(client):
    r = client.get("/static/bg-remove-worker.js")
    assert r.status_code == 200
    js = r.text
    assert "@huggingface/transformers@4.3.1" in js       # Apache-2.0
    assert "onnx-community/ormbg-ONNX" in js             # Apache-2.0 model
    assert "@imgly" not in js and "ISNet-ONNX" not in js  # AGPL: never ship these


def test_remove_background_has_no_server_endpoint(client):
    assert client.post("/api/convert/remove-background").status_code in (404, 405)


# ---------------- QR Code Generator ----------------

def test_qr_generates_scannable_size_png(client):
    r = client.post("/api/convert/qr-code-generator", data={"text": "https://purefileconverter.com"})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "qr-code.png"
    img = Image.open(io.BytesIO(download(client, res)))
    assert img.format == "PNG" and img.width == img.height and 800 <= img.width <= 1100
    assert img.getpixel((2, 2)) == 255                    # white quiet zone


def test_qr_rejects_empty_and_too_long(client):
    assert client.post("/api/convert/qr-code-generator", data={"text": "   "}).status_code == 400
    r = client.post("/api/convert/qr-code-generator", data={"text": "x" * (server.QR_MAX_CHARS + 1)})
    assert r.status_code == 400 and str(server.QR_MAX_CHARS) in r.json()["detail"]


def test_qr_handles_unicode(client):
    r = client.post("/api/convert/qr-code-generator", data={"text": "Café ☕ 東京"})
    assert r.status_code == 200, r.text


def test_qr_page_has_text_form_not_dropzone(client):
    html = client.get("/qr-code-generator").text
    assert 'id="qrForm"' in html and 'id="dropzone"' not in html


# ---------------- GIF to MP4 ----------------

def make_gif(w=200, h=120, frames=6, transparent=False) -> bytes:
    imgs = []
    for i in range(frames):
        im = Image.new("RGBA" if transparent else "RGB", (w, h),
                       (0, 0, 0, 0) if transparent else (i * 40 % 255, 100, 200))
        im.paste((255, 0, 0, 255) if transparent else (255, 255, 0), (i * 10, 10, i * 10 + 30, 40))
        imgs.append(im)
    buf = io.BytesIO()
    imgs[0].save(buf, "GIF", save_all=True, append_images=imgs[1:], duration=100, loop=0,
                 disposal=2, **({"transparency": 0} if transparent else {}))
    return buf.getvalue()


def probe(data: bytes, tmp_path):
    p = tmp_path / "out.mp4"
    p.write_bytes(data)
    ffprobe = shutil.which("ffprobe") or (server.FFMPEG_PATH or "").replace("ffmpeg", "ffprobe")
    if not ffprobe or not os.path.exists(ffprobe) and not shutil.which(ffprobe):
        return None
    out = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,width,height,pix_fmt", "-of", "json", str(p)],
                         capture_output=True, text=True)
    return json.loads(out.stdout)["streams"][0] if out.returncode == 0 else None


@pytest.mark.skipif(not server.FFMPEG_PATH, reason="ffmpeg not available")
@pytest.mark.parametrize("w,h,transparent", [(200, 120, False), (201, 101, True), (1600, 900, False)])
def test_gif_to_mp4_outputs_h264(client, tmp_path, w, h, transparent):
    r = client.post("/api/convert/gif-to-mp4",
                    files={"file": ("anim.gif", make_gif(w, h, transparent=transparent), "image/gif")})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "anim.mp4"
    data = download(client, res)
    assert data[4:8] == b"ftyp"
    info = probe(data, tmp_path)
    if info:
        assert info["codec_name"] == "h264" and info["pix_fmt"] == "yuv420p"
        assert info["width"] % 2 == 0 and info["height"] % 2 == 0
        assert max(info["width"], info["height"]) <= server.GIF_TO_MP4_MAX_SIDE


@pytest.mark.skipif(not server.FFMPEG_PATH, reason="ffmpeg not available")
def test_gif_to_mp4_rejects_garbage_and_cleans_up(client):
    before = set(os.listdir(server.TEMP_DIR))
    r = client.post("/api/convert/gif-to-mp4", files={"file": ("x.gif", b"GIF89a-not-really", "image/gif")})
    assert r.status_code == 400
    assert set(os.listdir(server.TEMP_DIR)) <= before


# ---------------- Blog: CTAs + affiliate coverage ----------------

@pytest.mark.parametrize("article,tool", [
    ("how-to-remove-image-background", "/remove-background"),
    ("how-to-make-image-transparent", "/remove-background"),
    ("how-to-convert-gif-to-mp4", "/gif-to-mp4"),
])
def test_v13_articles_point_to_new_tools(client, article, tool):
    assert BLOG_ARTICLES[article]["tool_link"] == tool
    html = client.get(f"/blog/{article}").text
    assert f'href="{tool}"' in html
    assert "Use the free Image Converter" not in html


def test_every_article_has_a_tagged_affiliate_link():
    for slug, a in BLOG_ARTICLES.items():
        links = [b["link"] for b in a["content_blocks"] if b["type"] == "affiliate"]
        assert links, slug
        for link in links:
            assert link.startswith("https://www.amazon.com/s?k=") and link.endswith("&tag=purefileconve-20"), link


# ---------------- Social share card ----------------

def test_og_image_is_1200x630_png(client):
    r = client.get("/static/og-image.png")
    assert r.status_code == 200
    img = Image.open(io.BytesIO(r.content))
    assert img.format == "PNG" and img.size == (1200, 630)
    assert len(r.content) < 300_000


def test_pages_use_png_share_card(client):
    for p in ["/", "/remove-background", "/blog/how-to-convert-pdf-to-word"]:
        html = client.get(p).text
        assert f'<meta property="og:image" content="{server.SITE_URL}/static/og-image.png">' in html, p
        assert f'<meta name="twitter:image" content="{server.SITE_URL}/static/og-image.png">' in html, p
        assert '<meta property="og:image:width" content="1200">' in html
        assert "og-image.svg\">" not in html.split("</head>")[0].split("og:url")[1][:400]
