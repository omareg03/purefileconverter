"""PDF Tools suite: Merge, Split, Compress, Rotate PDF + SEO parity."""
import io
import json
import re
import zipfile

import pytest
from pypdf import PdfReader, PdfWriter

import server
from blog_data import BLOG_ARTICLES
from conftest import assert_article_cta_or_redirect, make_pdf

PDF_TOOLS = ["merge-pdf", "split-pdf", "compress-pdf", "rotate-pdf"]


def download(client, result):
    assert server.FILE_ID_RE.match(result["file_id"]), result
    r = client.get(f"/api/download/{result['file_id']}")
    assert r.status_code == 200
    return r.content


def pages(data: bytes) -> int:
    return len(PdfReader(io.BytesIO(data)).pages)


# ---------------- Merge ----------------

def test_merge_pdf_combines_in_order(client):
    files = [("files", ("a.pdf", make_pdf(2), "application/pdf")),
             ("files", ("b.pdf", make_pdf(3), "application/pdf"))]
    r = client.post("/api/convert/merge-pdf", files=files)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "merged.pdf"
    assert pages(download(client, res)) == 5


def test_merge_pdf_needs_two_files(client):
    r = client.post("/api/convert/merge-pdf", files=[("files", ("a.pdf", make_pdf(1), "application/pdf"))])
    assert r.status_code == 400
    assert "at least 2" in r.json()["detail"]


def test_merge_pdf_rejects_too_many_files(client):
    files = [("files", (f"{i}.pdf", make_pdf(1), "application/pdf")) for i in range(server.MERGE_MAX_FILES + 1)]
    r = client.post("/api/convert/merge-pdf", files=files)
    assert r.status_code == 400


def test_merge_pdf_rejects_garbage(client):
    files = [("files", ("a.pdf", make_pdf(1), "application/pdf")),
             ("files", ("b.pdf", b"not a pdf", "application/pdf"))]
    assert client.post("/api/convert/merge-pdf", files=files).status_code == 400


# ---------------- Split ----------------

def test_split_pdf_all_pages_zip(client):
    r = client.post("/api/convert/split-pdf", files={"file": ("doc.pdf", make_pdf(3), "application/pdf")})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "doc_split.zip"
    zf = zipfile.ZipFile(io.BytesIO(download(client, res)))
    assert zf.namelist() == ["doc-page-1.pdf", "doc-page-2.pdf", "doc-page-3.pdf"]
    assert all(pages(zf.read(n)) == 1 for n in zf.namelist())


@pytest.mark.parametrize("spec,expected", [("1,3", 2), ("2-4", 3), ("1-2, 5", 3), (" 4 ", 1)])
def test_split_pdf_extract_range(client, spec, expected):
    r = client.post("/api/convert/split-pdf", files={"file": ("doc.pdf", make_pdf(5), "application/pdf")},
                    data={"pages": spec})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "doc_pages.pdf"
    assert pages(download(client, res)) == expected


@pytest.mark.parametrize("spec", ["0", "6", "3-1", "abc", "1-999999"])
def test_split_pdf_bad_range(client, spec):
    r = client.post("/api/convert/split-pdf", files={"file": ("doc.pdf", make_pdf(5), "application/pdf")},
                    data={"pages": spec})
    assert r.status_code == 400


# ---------------- Compress ----------------

def _photo_pdf() -> bytes:
    import random
    from PIL import Image
    random.seed(1)
    img = Image.effect_noise((1200, 1200), 60).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "PDF", resolution=150, quality=100)
    return buf.getvalue()


def test_compress_pdf_reduces_image_heavy_file(client):
    src = _photo_pdf()
    r = client.post("/api/convert/compress-pdf", files={"file": ("scan.pdf", src, "application/pdf")})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "scan_compressed.pdf"
    out = download(client, res)
    assert pages(out) == 1
    assert len(out) < len(src)


def test_compress_pdf_never_bigger_than_input(client):
    src = make_pdf(2)
    out = download(client, client.post("/api/convert/compress-pdf",
                                       files={"file": ("t.pdf", src, "application/pdf")}).json())
    assert len(out) <= len(src) and pages(out) == 2


# ---------------- Rotate ----------------

@pytest.mark.parametrize("angle", [90, 180, 270])
def test_rotate_pdf(client, angle):
    r = client.post("/api/convert/rotate-pdf", files={"file": ("r.pdf", make_pdf(2), "application/pdf")},
                    data={"angle": str(angle)})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["filename"] == "r_rotated.pdf"
    rd = PdfReader(io.BytesIO(download(client, res)))
    assert [p.rotation % 360 for p in rd.pages] == [angle, angle]


def test_rotate_pdf_bad_angle(client):
    r = client.post("/api/convert/rotate-pdf", files={"file": ("r.pdf", make_pdf(1), "application/pdf")},
                    data={"angle": "45"})
    assert r.status_code == 400


# ---------------- Shared guards ----------------

def test_encrypted_pdf_friendly_error(client):
    w = PdfWriter()
    w.add_blank_page(612, 792)
    w.encrypt("secret")
    buf = io.BytesIO()
    w.write(buf)
    r = client.post("/api/convert/compress-pdf", files={"file": ("locked.pdf", buf.getvalue(), "application/pdf")})
    assert r.status_code == 400
    assert "password" in r.json()["detail"].lower()


def test_pdf_tools_page_cap(client):
    r = client.post("/api/convert/rotate-pdf",
                    files={"file": ("big.pdf", make_pdf(server.PDF_TOOLS_MAX_PAGES + 1), "application/pdf")},
                    data={"angle": "90"})
    assert r.status_code == 400
    assert str(server.PDF_TOOLS_MAX_PAGES) in r.json()["detail"]


def test_merge_upload_cap(client):
    half = b"%PDF-1.4\n" + b"0" * (6 * 1024 * 1024)
    files = [("files", ("a.pdf", half, "application/pdf")), ("files", ("b.pdf", half, "application/pdf"))]
    assert client.post("/api/convert/merge-pdf", files=files).status_code == 413


# ---------------- SEO / branding parity ----------------

def jsonld(html):
    return [json.loads(b.replace("<\\/", "</"))
            for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


@pytest.mark.parametrize("slug", PDF_TOOLS)
def test_pdf_tool_page_seo(client, slug):
    tool = server.TOOLS_CONFIG[slug]
    html = client.get(f"/{slug}").text
    title = re.search(r"<title>(.*?)</title>", html).group(1)
    assert "– Convert" not in title and "Any Format" not in title, title
    assert tool["title"] in title and "PureFileConverter" in title and len(title) <= 70, title
    desc = re.search(r'<meta name="description" content="(.*?)">', html).group(1)
    assert 70 <= len(desc) <= 165, (len(desc), desc)
    assert tool["intro"] in html                      # indexable intro paragraph is visible
    assert {"WebApplication", "FAQPage", "BreadcrumbList"} <= {b["@type"] for b in jsonld(html)}
    assert f"<h1" in html and tool["title"] in html
    sm = client.get("/sitemap.xml").text
    assert f"{server.SITE_URL}/{slug}</loc>" in sm
    assert f"{server.SITE_URL}/{slug})" in client.get("/llms.txt").text
    assert f'href="/{slug}"' in client.get("/").text


def test_pdf_tools_category_on_homepage(client):
    html = client.get("/").text
    assert ">PDF Tools<" in html


def test_every_tool_shows_its_intro(client):
    for slug, tool in server.TOOLS_CONFIG.items():
        assert tool["intro"] in client.get(f"/{slug}").text, slug


def test_every_tool_title_is_clean(client):
    for slug in server.TOOLS_CONFIG:
        title = re.search(r"<title>(.*?)</title>", client.get(f"/{slug}").text).group(1)
        assert "Any Format" not in title and "Convert Merge" not in title, (slug, title)


def test_css_is_cache_busted(client):
    assert re.search(r'href="/static/tailwind\.css\?v=[\w.-]+"', client.get("/").text)


@pytest.mark.parametrize("article,tool", [
    ("how-to-merge-pdf-files", "/merge-pdf"),
    ("how-to-split-pdf-files", "/split-pdf"),
    ("how-to-compress-pdf-files", "/compress-pdf"),
    ("best-free-pdf-compressors", "/compress-pdf"),
])
def test_pdf_articles_point_to_pdf_tools(client, article, tool):
    assert_article_cta_or_redirect(client, article, tool)


def _bomb_pdf() -> bytes:
    """<1 MB PDF whose content stream inflates to ~60 MB (over the 25 MB per-stream cap)."""
    import zlib
    from pypdf.generic import NameObject, NumberObject, StreamObject
    payload = zlib.compress(b"0" * 60_000_000, 9)
    w = PdfWriter()
    page = w.add_blank_page(612, 792)
    s = StreamObject()
    s._data = payload
    s[NameObject("/Filter")] = NameObject("/FlateDecode")
    s[NameObject("/Length")] = NumberObject(len(payload))
    page[NameObject("/Contents")] = w._add_object(s)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


@pytest.mark.parametrize("ep,data", [("compress-pdf", {}), ("split-pdf", {"pages": "1"}),
                                     ("rotate-pdf", {"angle": "90"})])
def test_decompression_bomb_is_bounded(client, ep, data):
    import tracemalloc
    tracemalloc.start()
    r = client.post(f"/api/convert/{ep}", files={"file": ("bomb.pdf", _bomb_pdf(), "application/pdf")}, data=data)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert r.status_code in (200, 400)
    assert peak < 120 * 1024 * 1024, f"{ep} peaked at {peak // 2**20} MB"
