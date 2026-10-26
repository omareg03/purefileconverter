"""Blog articles for PureFileConverter (v1.4, October 2026).

17 hand-written guides, one per real task the site's tools solve. The article content lives in the
blog_posts package; this module collects it and derives the display fields the templates need.
The 133 thin, templated articles removed in v1.4 redirect via blog_redirects.py.
"""
import math
from datetime import date

from blog_posts import documents, images_a, images_b, media_faq, pdf_word

CATEGORY_ORDER = ["Document Guides", "Image Guides", "Media Guides", "Troubleshooting", "FAQ"]
WORDS_PER_MINUTE = 220


def _prose_words(article: dict) -> int:
    words = 0
    for block in article["content_blocks"]:
        if block["type"] in ("paragraph", "callout", "heading", "subheading"):
            words += len(block["text"].split())
        elif block["type"] in ("list", "ordered"):
            words += sum(len(entry.split()) for entry in block["entries"])
    return words


def _label(iso_date: str) -> str:
    d = date.fromisoformat(iso_date)
    return f"{d:%B} {d.day}, {d.year}"


BLOG_ARTICLES = {}
for _article in pdf_word.ARTICLES + documents.ARTICLES + images_a.ARTICLES + images_b.ARTICLES + media_faq.ARTICLES:
    assert _article["slug"] not in BLOG_ARTICLES, _article["slug"]
    assert _article["category"] in CATEGORY_ORDER, _article["category"]
    BLOG_ARTICLES[_article["slug"]] = {
        **_article,
        "reading_time": max(1, math.ceil(_prose_words(_article) / WORDS_PER_MINUTE)),
        "published": "Updated " + _label(_article["date_modified"]),
    }

BLOG_CATEGORIES = [(cat, [s for s, a in BLOG_ARTICLES.items() if a["category"] == cat]) for cat in CATEGORY_ORDER]
BLOG_CATEGORIES = [(cat, slugs) for cat, slugs in BLOG_CATEGORIES if slugs]
