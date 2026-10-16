"""Search Console 'Page with redirect' guards: every URL we publish must answer 200 directly."""
import re

import server
from blog_data import BLOG_ARTICLES
from conftest import sitemap_paths

HTML = {"accept": "text/html"}


def test_sitemap_urls_direct_200(client):
    for p in sitemap_paths(client):
        r = client.get(p, headers=HTML)
        assert r.status_code == 200, f"{p} -> {r.status_code} {r.headers.get('location')}"


def test_internal_links_direct_200(client):
    hrefs = {}
    for p in sitemap_paths(client):
        for h in re.findall(r'href="(/[^"#?]*)', client.get(p).text):
            hrefs.setdefault(h, p)
    assert len(hrefs) > 150
    for h, src in hrefs.items():
        r = client.get(h, headers=HTML)
        assert r.status_code == 200, f"{h} (linked from {src}) -> {r.status_code} {r.headers.get('location')}"


def test_blog_tool_links_point_to_real_tools():
    for slug, a in BLOG_ARTICLES.items():
        link = a["tool_link"]
        assert link == "/" or link.lstrip("/") in server.TOOLS_CONFIG, (slug, link)


def test_trailing_slash_is_single_permanent_redirect(client):
    for p in ["/blog/", "/pdf-to-word/", "/blog/how-to-convert-pdf-to-word/"]:
        r = client.get(p, headers=HTML)
        assert r.status_code == 301, (p, r.status_code)
        assert r.headers["location"] == server.SITE_URL + p.rstrip("/")


def test_trailing_slash_keeps_query(client):
    r = client.get("/blog/?utm_source=x")
    assert r.status_code == 301
    assert r.headers["location"] == server.SITE_URL + "/blog?utm_source=x"


def test_homepage_and_static_untouched(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/tailwind.css").status_code == 200


def test_trailing_slash_redirect_cannot_be_abused_as_open_redirect(client):
    r = client.get("http://testserver//evil.com/")
    assert r.status_code in (301, 404)
    if r.status_code == 301:
        assert r.headers["location"].startswith(server.SITE_URL + "/")


def test_organization_sameas_uses_current_brand(client):
    html = client.get("/").text
    assert "github.com/omareg03/purefileconverter" in html
    assert "cleanfileconverter" not in html.lower()


def test_trailing_slash_redirect_reencodes_path(client):
    r = client.get("/caf%E2%82%AC/")
    assert r.status_code == 301
    assert r.headers["location"] == server.SITE_URL + "/caf%E2%82%AC"
    r = client.get("/a%3Fb%0D%0AX-Evil:1/")
    assert r.status_code == 301
    loc = r.headers["location"]
    assert "\r" not in loc and "\n" not in loc and "?" not in loc
