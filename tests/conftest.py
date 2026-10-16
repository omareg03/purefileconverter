import io
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("ADSENSE_CLIENT_ID", "ca-pub-8373498789989542")
os.environ.setdefault("RATE_LIMIT_MAX", "20")

import server  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    server.rate_limiter.hits.clear()
    yield
    server.rate_limiter.hits.clear()


@pytest.fixture(scope="session")
def client():
    return TestClient(server.app, follow_redirects=False)


def make_pdf(pages: int) -> bytes:
    """Build an N-page Letter-size PDF in memory with Pillow (no binary fixtures)."""
    imgs = [Image.new("RGB", (612, 792), (255, 255, 255 - (i * 7) % 255)) for i in range(pages)]
    buf = io.BytesIO()
    imgs[0].save(buf, "PDF", save_all=True, append_images=imgs[1:], resolution=72)
    return buf.getvalue()


def sitemap_paths(client):
    import re
    xml = client.get("/sitemap.xml").text
    return [u.replace(server.SITE_URL, "") or "/" for u in re.findall(r"<loc>([^<]+)</loc>", xml)]
