"""Hand-written blog articles for PureFileConverter (v1.4).

Each module in this package defines ARTICLES, a list of article dicts. blog_data.py collects them.
The helpers below build the content blocks that blog_article.html knows how to render.
"""


def P(text: str) -> dict:
    return {"type": "paragraph", "text": text}


def H(text: str) -> dict:
    return {"type": "heading", "text": text}


def SUB(text: str) -> dict:
    return {"type": "subheading", "text": text}


def L(*entries: str) -> dict:
    return {"type": "list", "entries": list(entries)}


def O(*entries: str) -> dict:  # noqa: E743 - ordered list block
    return {"type": "ordered", "entries": list(entries)}


def C(text: str) -> dict:
    return {"type": "callout", "text": text}


def IMG(src: str, alt: str, caption: str = "") -> dict:
    return {"type": "image", "src": src, "alt": alt, "width": "720", "height": "400", "caption": caption or alt}


def AFF(title: str, description: str, query: str) -> dict:
    """Amazon search link (never a guessed /dp/ ASIN) carrying the Associates tag."""
    return {"type": "affiliate", "title": title, "description": description,
            "link": f"https://www.amazon.com/s?k={query}&tag=purefileconve-20"}
