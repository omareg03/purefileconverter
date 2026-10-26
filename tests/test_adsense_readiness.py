"""v1.4 AdSense readiness: friendly 404, no ads on utility screens, no thin or duplicate blog content,
real trust pages, affiliate disclosure, substantive tool pages."""
import re

import server
from blog_data import BLOG_ARTICLES, BLOG_CATEGORIES
from blog_redirects import REMOVED_ARTICLE_REDIRECTS
from conftest import sitemap_paths

HTML = {"accept": "text/html"}
ADSENSE_JS = "adsbygoogle.js"

# The 15 hand-written originals + 2 rewritten guides for tools that had none (HEIC, Compress PDF).
KEPT_ARTICLES = {
    "how-to-convert-pdf-to-word", "why-pdf-to-word-loses-formatting", "how-to-convert-pdf-to-word-google-docs",
    "how-to-extract-text-from-pdf", "how-to-convert-word-to-pdf", "how-to-convert-csv-to-excel",
    "how-to-compress-pdf-files", "what-is-webp-why-use-it", "jpg-vs-png-vs-webp-guide",
    "how-to-convert-png-to-jpg", "how-to-compress-jpg-images", "how-to-resize-images-online",
    "how-to-convert-heic-to-jpg", "how-to-extract-audio-from-mp4", "how-to-convert-wav-to-mp3",
    "how-to-convert-avi-to-mp4", "is-it-safe-to-convert-files-online",
}


def main_text(html: str) -> str:
    m = re.search(r"(?is)<main[^>]*>(.*)</main>", html)
    body = m.group(1) if m else html
    body = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", " ", body)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", body)).strip()


def word_count(html: str) -> int:
    return len(main_text(html).split())


# ---------------- 404 + utility screens ----------------

def test_unknown_page_is_friendly_404_not_500(client):
    r = client.get("/this-page-does-not-exist", headers=HTML)
    assert r.status_code == 404
    assert "Page not found" in r.text
    assert '<meta name="robots" content="noindex, nofollow">' in r.text
    assert 'href="/#tools"' in r.text and 'href="/blog"' in r.text


def test_unknown_blog_article_is_friendly_404(client):
    r = client.get("/blog/no-such-article-here", headers=HTML)
    assert r.status_code == 404
    assert "Page not found" in r.text


def test_no_adsense_on_screens_without_publisher_content(client):
    r = client.get("/this-page-does-not-exist", headers=HTML)
    assert ADSENSE_JS not in r.text
    assert ADSENSE_JS in client.get("/").text


# ---------------- Blog pruning: thin, near-duplicate articles removed ----------------

def blog_links(text: str) -> set:
    return set(re.findall(r"/blog/([a-z0-9-]+)", text))


def test_blog_keeps_only_the_17_original_guides():
    assert set(BLOG_ARTICLES) == KEPT_ARTICLES


def test_blog_categories_list_every_live_article_once():
    listed = [s for _, slugs in BLOG_CATEGORIES for s in slugs]
    assert sorted(listed) == sorted(BLOG_ARTICLES)
    assert all(slugs for _, slugs in BLOG_CATEGORIES)


def test_removed_articles_redirect_permanently_to_a_live_page(client):
    assert len(REMOVED_ARTICLE_REDIRECTS) == 133
    assert not set(REMOVED_ARTICLE_REDIRECTS) & set(BLOG_ARTICLES)
    for slug, target in REMOVED_ARTICLE_REDIRECTS.items():
        r = client.get(f"/blog/{slug}", headers=HTML)
        assert r.status_code == 301, slug
        assert r.headers["location"] == server.SITE_URL + target, slug
        assert client.get(target, headers=HTML).status_code == 200, (slug, target)


def test_sitemap_lists_only_live_pages(client):
    pages = sitemap_paths(client)
    assert len(pages) == 1 + len(server.TOOLS_CONFIG) + len(server.LEGAL_PAGES) + 1 + len(KEPT_ARTICLES)
    assert {p[len("/blog/"):] for p in pages if p.startswith("/blog/")} == KEPT_ARTICLES


def test_no_page_links_to_a_removed_article(client):
    for p in sitemap_paths(client) + ["/llms.txt"]:
        assert not blog_links(client.get(p).text) & set(REMOVED_ARTICLE_REDIRECTS), p


def test_llms_txt_lists_every_live_article(client):
    llms = client.get("/llms.txt").text
    for slug in BLOG_ARTICLES:
        assert f"{server.SITE_URL}/blog/{slug})" in llms, slug
    assert f"{len(BLOG_ARTICLES)} in-depth" in llms


# ---------------- Affiliate disclosure (Amazon Operating Agreement + FTC) ----------------

AMAZON_DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases"


def test_amazon_disclosure_in_footer_of_every_page(client):
    for p in sitemap_paths(client):
        assert AMAZON_DISCLOSURE in client.get(p).text, p


def test_articles_disclose_right_next_to_affiliate_links(client):
    with_links = [s for s, a in BLOG_ARTICLES.items() if any(b["type"] == "affiliate" for b in a["content_blocks"])]
    assert with_links
    for slug in with_links:
        assert AMAZON_DISCLOSURE in main_text(client.get(f"/blog/{slug}").text), slug


# ---------------- Trust pages: who runs the site, how to reach them, how data is handled ----------------

def test_about_page_says_who_runs_the_site_and_how_it_works(client):
    html = client.get("/about").text
    text = main_text(html)
    assert word_count(html) >= 350
    for phrase in ("Omy Grace", "Florida", "LibreOffice", "FFmpeg", "1 hour", "advertising"):
        assert phrase in text, phrase
    assert 'href="/contact"' in html


def test_contact_page_has_a_real_address_and_guidance(client):
    html = client.get("/contact").text
    assert word_count(html) >= 150
    assert 'href="mailto:support@purefileconverter.com"' in html
    assert "cleanfileconverter" not in html


def test_privacy_policy_covers_files_cookies_ads_and_affiliates(client):
    html = client.get("/privacy").text
    text = main_text(html)
    assert len(text.split()) >= 700
    for phrase in ("Third-party vendors, including Google, use cookies to serve ads",
                   "Google's use of advertising cookies enables it and its partners",
                   "Google Analytics", AMAZON_DISCLOSURE, "1 hour", "in your browser",
                   "support@purefileconverter.com", server.LEGAL_UPDATED):
        assert phrase in text, phrase
    for url in ("https://adssettings.google.com", "https://www.aboutads.info",
                "https://policies.google.com/technologies/partner-sites"):
        assert f'href="{url}' in html, url


def test_terms_are_substantive(client):
    text = main_text(client.get("/terms").text)
    assert len(text.split()) >= 450
    for phrase in ("rights", "1 hour", "Florida", "support@purefileconverter.com", server.LEGAL_UPDATED):
        assert phrase in text, phrase


def test_no_page_claims_to_be_ad_free(client):
    for p in sitemap_paths(client) + ["/llms.txt"]:
        low = main_text(client.get(p).text).lower()
        for claim in ("ad-free", "no ads", "zero ads", "without ads"):
            assert claim not in low, (p, claim)


# ---------------- Tool pages: substantial, unique, tool-specific help ----------------

def shingles(text: str, k: int = 5) -> set:
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(w[i:i + k]) for i in range(len(w) - k + 1)}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def test_every_tool_has_a_written_guide():
    from tool_content import TOOL_GUIDES
    assert set(TOOL_GUIDES) == set(server.TOOLS_CONFIG)
    for slug, g in TOOL_GUIDES.items():
        assert len(g["steps"]) >= 3, slug
        assert len(" ".join(g["body"]).split()) >= 170, slug


def test_tool_guides_are_not_templated():
    from tool_content import TOOL_GUIDES
    sh = {s: shingles(" ".join(g["body"] + g["steps"])) for s, g in TOOL_GUIDES.items()}
    slugs = sorted(sh)
    for i, a in enumerate(slugs):
        for b in slugs[i + 1:]:
            assert jaccard(sh[a], sh[b]) < 0.10, (a, b)


def test_tool_pages_render_guide_and_have_substantial_text(client):
    for slug, tool in server.TOOLS_CONFIG.items():
        html = client.get(f"/{slug}").text
        assert f"How to use the {tool['title']} tool" in html, slug
        assert word_count(html) >= 450, (slug, word_count(html))


def test_tool_pages_link_their_in_depth_guide(client):
    from tool_content import TOOL_GUIDES
    linked = {s: g["article"] for s, g in TOOL_GUIDES.items() if g.get("article")}
    assert len(linked) >= 11
    for slug, article in linked.items():
        assert article in BLOG_ARTICLES, (slug, article)
        assert f'href="/blog/{article}"' in client.get(f"/{slug}").text, slug


# ---------------- Claims on the page match what the converter really does ----------------

def _audio_codec_of(data: bytes, suffix: str) -> str:
    import os
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
    try:
        err = subprocess.run([server.FFMPEG_PATH, "-hide_banner", "-i", f.name], capture_output=True, text=True).stderr
    finally:
        os.remove(f.name)
    m = re.search(r"Audio: (\w+)", err)
    return m.group(1) if m else ""


def _make_media(args: list, suffix: str) -> bytes:
    import os
    import subprocess
    import tempfile
    out = tempfile.NamedTemporaryFile(suffix=suffix, delete=False).name
    try:
        subprocess.run([server.FFMPEG_PATH, "-hide_banner", "-loglevel", "error", "-y", *args, out], check=True)
        return open(out, "rb").read()
    finally:
        os.remove(out)


def test_video_outputs_use_aac_audio_as_the_pages_say(client):
    avi = _make_media(["-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10", "-f", "lavfi", "-i",
                       "sine=duration=2", "-c:v", "mpeg4", "-c:a", "libmp3lame", "-shortest"], ".avi")
    mp3 = _make_media(["-f", "lavfi", "-i", "sine=duration=2", "-c:a", "libmp3lame"], ".mp3")
    for endpoint, name, data in (("avi-to-mp4", "clip.avi", avi), ("mp3-to-mp4", "song.mp3", mp3)):
        r = client.post(f"/api/convert/{endpoint}", files={"file": (name, data)})
        assert r.status_code == 200, r.text
        out = client.get(f"/api/download/{r.json()['file_id']}").content
        assert _audio_codec_of(out, ".mp4") == "aac", endpoint


# ---------------- Blog articles: substantial, original, honest ----------------

ARTICLE_TOOLS = {
    "how-to-convert-pdf-to-word": "/pdf-to-word", "why-pdf-to-word-loses-formatting": "/pdf-to-word",
    "how-to-convert-pdf-to-word-google-docs": "/pdf-to-word", "how-to-extract-text-from-pdf": "/pdf-to-word",
    "how-to-convert-word-to-pdf": "/word-to-pdf", "how-to-convert-csv-to-excel": "/csv-to-excel",
    "how-to-compress-pdf-files": "/compress-pdf", "what-is-webp-why-use-it": "/image-converter",
    "jpg-vs-png-vs-webp-guide": "/image-converter", "how-to-convert-png-to-jpg": "/image-converter",
    "how-to-compress-jpg-images": "/compress-image", "how-to-resize-images-online": "/image-resizer",
    "how-to-convert-heic-to-jpg": "/heic-to-jpg", "how-to-extract-audio-from-mp4": "/mp4-to-mp3",
    "how-to-convert-wav-to-mp3": "/wav-to-mp3", "how-to-convert-avi-to-mp4": "/avi-to-mp4",
    "is-it-safe-to-convert-files-online": "/",
}


def article_prose(a: dict) -> str:
    parts = []
    for b in a["content_blocks"]:
        if b["type"] in ("paragraph", "callout"):
            parts.append(b["text"])
        elif b["type"] in ("list", "ordered"):
            parts.extend(b["entries"])
    return " ".join(parts)


def article_schema(html: str) -> dict:
    import json
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return next(d for d in (json.loads(b.replace("<\/", "</")) for b in blocks) if d.get("@type") == "Article")


def test_every_article_has_at_least_800_words_of_real_writing():
    for slug, a in BLOG_ARTICLES.items():
        n = len(article_prose(a).split())
        assert n >= 800, (slug, n)


def test_articles_do_not_share_templated_text():
    sh = {s: shingles(article_prose(a)) for s, a in BLOG_ARTICLES.items()}
    slugs = sorted(sh)
    for i, x in enumerate(slugs):
        for y in slugs[i + 1:]:
            assert jaccard(sh[x], sh[y]) < 0.05, (x, y)


def test_old_template_boilerplate_is_gone(client):
    banned = ("makes it fast, free and simple", "is a task people run into constantly",
              "Getting it right saves time", "Compress large files first if you hit an upload limit", "We tested")
    for slug in BLOG_ARTICLES:
        text = main_text(client.get(f"/blog/{slug}").text)
        for phrase in banned:
            assert phrase not in text, (slug, phrase)


def test_article_ctas_open_a_tool_that_accepts_that_file_type():
    assert {s: a["tool_link"] for s, a in BLOG_ARTICLES.items()} == ARTICLE_TOOLS


def test_affiliate_boxes_stay_a_minor_part_of_the_blog():
    counts = [sum(b["type"] == "affiliate" for b in a["content_blocks"]) for a in BLOG_ARTICLES.values()]
    assert max(counts) <= 1 and sum(counts) <= len(BLOG_ARTICLES) // 2


def test_articles_show_author_and_real_dates(client):
    for slug, a in BLOG_ARTICLES.items():
        html = client.get(f"/blog/{slug}").text
        assert 'By <a href="/about">Omy Grace</a>' in html, slug
        art = article_schema(html)
        assert art["author"] == {"@type": "Person", "name": "Omy Grace", "url": server.SITE_URL + "/about"}, slug
        assert (art["datePublished"], art["dateModified"]) == (a["date_published"], a["date_modified"]), slug
        assert art["image"].startswith(server.SITE_URL + "/static/"), slug


def test_removed_article_redirects_stay_on_this_site():
    for slug, target in REMOVED_ARTICLE_REDIRECTS.items():
        assert target.startswith("/") and not target.startswith("//") and "\\" not in target, (slug, target)


def test_homepage_explains_the_service_and_links_the_guides(client):
    html = client.get("/").text
    main_html = re.search(r"(?is)<main[^>]*>(.*)</main>", html).group(1)
    assert word_count(html) >= 500, word_count(html)
    assert "How PureFileConverter works" in main_html
    assert 'href="/about"' in main_html
    linked = blog_links(main_html) & set(BLOG_ARTICLES)
    assert len(linked) >= 6, linked
