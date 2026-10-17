"""Guardrails that must never regress (SEO, monetization, abuse limits)."""
import json
import re

import server
from blog_data import BLOG_ARTICLES
from conftest import sitemap_paths

HTML = {"accept": "text/html"}


def jsonld_types(html):
    return {json.loads(b.replace("<\\/", "</")).get("@type")
            for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)}


def test_every_sitemap_page_ok(client):
    paths = sitemap_paths(client)
    assert len(paths) >= 168
    for p in paths:
        assert client.get(p, headers=HTML).status_code == 200, p


def test_tool_pages_have_full_seo(client):
    for slug in server.TOOLS_CONFIG:
        html = client.get(f"/{slug}").text
        assert {"WebApplication", "FAQPage", "BreadcrumbList"} <= jsonld_types(html), slug
        assert "<details" in html and "Related" in html, slug
        assert f'<link rel="canonical" href="{server.SITE_URL}/{slug}">' in html


def test_home_and_blog_schema(client):
    assert {"WebSite", "Organization"} <= jsonld_types(client.get("/").text)
    assert "Article" in jsonld_types(client.get("/blog/how-to-convert-pdf-to-word").text)


def test_analytics_and_adsense_present(client):
    html = client.get("/").text
    assert "G-QL5VKVW6P7" in html
    assert "ca-pub-8373498789989542" in html
    assert client.get("/ads.txt").text.strip() == "google.com, pub-8373498789989542, DIRECT, f08c47fec0942fa0"


def test_no_placeholder_ad_boxes(client):
    for p in ["/", "/pdf-to-word", "/blog", "/blog/how-to-convert-pdf-to-word"]:
        assert "[ Advertisement ]" not in client.get(p).text


def test_robots_and_llms(client):
    robots = client.get("/robots.txt").text
    for bot in ["GPTBot", "OAI-SearchBot", "PerplexityBot", "ClaudeBot", "Google-Extended"]:
        assert f"User-agent: {bot}" in robots
    assert f"Sitemap: {server.SITE_URL}/sitemap.xml" in robots
    llms = client.get("/llms.txt").text
    for slug in server.TOOLS_CONFIG:
        assert f"{server.SITE_URL}/{slug})" in llms, slug


def test_affiliate_links_tagged_and_no_guessed_asins():
    links = [b["link"] for a in BLOG_ARTICLES.values() for b in a["content_blocks"] if b["type"] == "affiliate"]
    assert len(links) >= 145
    for link in links:
        assert "tag=purefileconve-20" in link and "/dp/" not in link, link


def test_blog_has_150_articles_with_images():
    assert len(BLOG_ARTICLES) == 150
    for slug, a in BLOG_ARTICLES.items():
        imgs = [b for b in a["content_blocks"] if b["type"] == "image"]
        assert imgs and all(i["alt"] and i["width"] and i["height"] for i in imgs), slug


def test_upload_cap_413(client):
    big = b"0" * (int(server.MAX_UPLOAD_MB * 1024 * 1024) + 2 * 1024 * 1024)
    r = client.post("/api/convert/pdf-to-word", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_rate_limit_429(client):
    codes = [client.post("/api/convert/image", files={"file": ("x.png", b"", "image/png")},
                         data={"format": "jpg"}).status_code for _ in range(server.RATE_LIMIT_MAX + 1)]
    assert codes[-1] == 429 and 429 not in codes[:-1]


def test_file_ttl_is_one_hour():
    assert server.FILE_TTL_SECONDS == 3600


def test_security_headers_on_pages_and_api(client):
    for path in ["/", "/merge-pdf", "/blog", "/sitemap.xml", "/health"]:
        h = client.get(path).headers
        assert h["x-content-type-options"] == "nosniff", path
        assert h["x-frame-options"] == "SAMEORIGIN", path
        assert "max-age=" in h["strict-transport-security"], path
        assert h["referrer-policy"] == "strict-origin-when-cross-origin", path
        assert "camera=()" in h["permissions-policy"], path
    assert "content-security-policy" not in client.get("/").headers  # would break AdSense/GA4


def test_no_debug_or_source_exposure(client):
    for path in ["/docs", "/redoc", "/openapi.json", "/.env", "/.git/config", "/server.py",
                 "/static/../server.py", "/api/download/..%2fserver.py"]:
        assert client.get(path).status_code == 404, path
