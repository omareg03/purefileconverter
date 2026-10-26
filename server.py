"""PureFileConverter - FastAPI backend.

Configuration (all optional, via environment variables):
    MAX_UPLOAD_MB            Max upload size per file in MB (default 10)
    SITE_URL                 Public base URL used for canonical/sitemap (default https://purefileconverter.com)
    CONTACT_EMAIL            Address shown on the contact page
    ADSENSE_CLIENT_ID        e.g. ca-pub-1234567890123456. When set, the real AdSense script is
                             injected and the grey placeholder boxes disappear.
    RATE_LIMIT_MAX           Conversions allowed per IP per window (default 20, 0 disables)
    RATE_LIMIT_WINDOW_SECONDS  Window length in seconds (default 600)
    MAX_CONCURRENT_CONVERSIONS Heavy jobs (office/audio/video) run at once (default 2)
    TRUST_PROXY_HEADERS      "1" to read the client IP from CF-Connecting-IP / X-Forwarded-For
                             (defaults to on when running on Render)
"""
import asyncio
import io
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
from collections import deque
from contextlib import asynccontextmanager, contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("cleanfileconverter")

IS_WINDOWS = sys.platform == "win32"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


MAX_UPLOAD_MB = _env_float("MAX_UPLOAD_MB", 10)          # single source of truth for the size limit
MAX_UPLOAD_BYTES = int(MAX_UPLOAD_MB * 1024 * 1024)
MULTIPART_OVERHEAD = 1024 * 1024                         # slack for multipart boundaries / form fields
DRAIN_CAP_BYTES = 64 * 1024 * 1024                       # drain oversize bodies up to this before replying 413

SITE_URL = os.environ.get("SITE_URL", "https://purefileconverter.com").rstrip("/")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "support@purefileconverter.com")  # same as render.yaml
LEGAL_UPDATED = "October 26, 2026"

FILE_TTL_SECONDS = 3600                                  # converted files are deleted after 1 hour
SWEEP_INTERVAL_SECONDS = 60

RATE_LIMIT_MAX = int(_env_float("RATE_LIMIT_MAX", 20))
RATE_LIMIT_WINDOW = int(_env_float("RATE_LIMIT_WINDOW_SECONDS", 600))
MAX_CONCURRENT_CONVERSIONS = max(1, int(_env_float("MAX_CONCURRENT_CONVERSIONS", 2)))
TRUST_PROXY = os.environ.get("TRUST_PROXY_HEADERS", "1" if os.environ.get("RENDER") else "0") == "1"


def _normalize_adsense_id(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if re.fullmatch(r"ca-pub-\d{8,20}", raw):
        return raw
    if re.fullmatch(r"pub-\d{8,20}", raw):
        return "ca-" + raw
    if re.fullmatch(r"\d{8,20}", raw):
        return "ca-pub-" + raw
    log.warning("ADSENSE_CLIENT_ID %r is not a valid publisher id; ignoring it.", raw)
    return ""


ADSENSE_CLIENT_ID = _normalize_adsense_id(os.environ.get("ADSENSE_CLIENT_ID", ""))

TEMP_DIR = os.path.join(tempfile.gettempdir(), "cleanfileconverter")
os.makedirs(TEMP_DIR, exist_ok=True)

GENERIC_FAILURE = ("Conversion failed. The file may be corrupted, password-protected, "
                   "or not a valid file of the expected type.")


def too_large_message() -> str:
    return (f"This file is too large. The maximum upload size is {MAX_UPLOAD_MB:g} MB. "
            "Please choose a smaller file and try again.")


# --------------------------------------------------------------------------- #
# External tools: ffmpeg, LibreOffice, optional Windows COM (Word / Excel)
# --------------------------------------------------------------------------- #

def locate_ffmpeg():
    """Prefer an explicit FFMPEG_BINARY, then the imageio-ffmpeg bundled binary, then system ffmpeg."""
    explicit = os.environ.get("FFMPEG_BINARY")
    if explicit and (os.path.exists(explicit) or shutil.which(explicit)):
        return explicit
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return shutil.which("ffmpeg")


FFMPEG_PATH = locate_ffmpeg()
if FFMPEG_PATH:
    os.environ["FFMPEG_BINARY"] = FFMPEG_PATH  # must be set before moviepy is imported

import pandas as pd                                    # noqa: E402
from pdf2docx import Converter                         # noqa: E402
from PIL import Image, ImageOps                        # noqa: E402
from moviepy import VideoFileClip, AudioFileClip, ColorClip  # noqa: E402
import pypdfium2 as pdfium                             # noqa: E402  (BSD-3/Apache-2.0, Chrome's PDF engine)
import pillow_heif                                     # noqa: E402  (BSD-3)
from pypdf import PdfReader, PdfWriter                 # noqa: E402  (BSD-3, pure Python: merge/split/rotate/compress)
from pypdf import Configuration as PdfConfiguration    # noqa: E402
from pypdf import apply_configuration as pdf_apply_configuration  # noqa: E402
import zipfile                                         # noqa: E402
import qrcode                                          # noqa: E402  (BSD, pure Python; renders via Pillow)

# Decompression-bomb guard for pypdf on a 512 MB instance: cap every decoded stream at 25 MB
# (defaults are 75 MB). Applied per request via a context manager (pypdf uses a ContextVar).
PDF_LIMITS = PdfConfiguration().with_overwrites(
    maximum_declared_stream_length=25_000_000,
    array_based_stream_maximum_output_length=25_000_000,
    jbig2_maximum_output_length=25_000_000,
    lzw_maximum_output_length=25_000_000,
    run_length_maximum_output_length=25_000_000,
    zlib_maximum_output_length=25_000_000,
)

pillow_heif.register_heif_opener()

# Windows-only imports are guarded so the server imports cleanly on Linux.
pythoncom = None
win32com_client = None
docx2pdf_convert = None
if sys.platform == "win32":
    try:
        import pythoncom
        import win32com.client as win32com_client
    except ImportError:
        pythoncom = None
        win32com_client = None
    try:
        from docx2pdf import convert as docx2pdf_convert
    except ImportError:
        docx2pdf_convert = None


def find_soffice():
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    if IS_WINDOWS:
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
            if base:
                candidate = os.path.join(base, "LibreOffice", "program", "soffice.exe")
                if os.path.exists(candidate):
                    return candidate
    return None


SOFFICE_PATH = find_soffice()
LO_PROFILE_DIR = os.path.join(tempfile.gettempdir(), "cleanfileconverter_lo_profile")
LO_TIMEOUT_SECONDS = 120
lo_lock = threading.Lock()      # one LibreOffice instance per profile at a time
word_lock = threading.Lock()
excel_lock = threading.Lock()
CONVERSION_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_CONVERSIONS)


def libreoffice_to_pdf(src: str, dst: str) -> None:
    """Convert a Word/Excel/CSV file to PDF with `soffice --headless --convert-to pdf`."""
    if not SOFFICE_PATH:
        raise RuntimeError("LibreOffice (soffice) not found")
    outdir = tempfile.mkdtemp(prefix="lo_", dir=TEMP_DIR)
    try:
        cmd = [
            SOFFICE_PATH,
            f"-env:UserInstallation={Path(LO_PROFILE_DIR).as_uri()}",
            "--headless", "--norestore", "--nolockcheck", "--nodefault",
            "--convert-to", "pdf", "--outdir", outdir, src,
        ]
        popen_kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
        if not IS_WINDOWS:
            popen_kwargs["start_new_session"] = True
        with lo_lock:
            proc = subprocess.Popen(cmd, **popen_kwargs)
            try:
                _, err = proc.communicate(timeout=LO_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                if IS_WINDOWS:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
                else:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                proc.communicate()
                raise RuntimeError("LibreOffice timed out")
        produced = os.path.join(outdir, Path(src).stem + ".pdf")
        if proc.returncode != 0 or not os.path.exists(produced):
            raise RuntimeError(f"LibreOffice failed (code {proc.returncode}): {err[-300:]!r}")
        shutil.move(produced, dst)
    finally:
        shutil.rmtree(outdir, ignore_errors=True)


def com_word_to_pdf(src: str, dst: str) -> None:
    if not (IS_WINDOWS and pythoncom and docx2pdf_convert):
        raise RuntimeError("Microsoft Word automation is not available")
    with word_lock:
        pythoncom.CoInitialize()
        try:
            docx2pdf_convert(src, dst)
        finally:
            pythoncom.CoUninitialize()


def com_excel_to_pdf(src: str, dst: str) -> None:
    if not (IS_WINDOWS and pythoncom and win32com_client):
        raise RuntimeError("Microsoft Excel automation is not available")
    with excel_lock:
        pythoncom.CoInitialize()
        try:
            excel = win32com_client.Dispatch("Excel.Application")
            excel.Visible = False
            try:
                wb = excel.Workbooks.Open(os.path.abspath(src))
                try:
                    wb.ExportAsFixedFormat(0, os.path.abspath(dst))
                finally:
                    wb.Close(False)
            finally:
                excel.Quit()
        finally:
            pythoncom.CoUninitialize()


def office_to_pdf(src: str, dst: str, com_fallback) -> None:
    """LibreOffice first (works on Linux/Render); Windows COM (Word/Excel) as optional fallback."""
    if SOFFICE_PATH:
        try:
            libreoffice_to_pdf(src, dst)
            return
        except Exception:
            log.exception("LibreOffice conversion failed; trying fallback if available")
            if os.path.exists(dst):
                os.remove(dst)
    if IS_WINDOWS:
        try:
            com_fallback(src, dst)
            return
        except Exception:
            log.exception("Microsoft Office COM conversion failed")
    if not SOFFICE_PATH and not IS_WINDOWS:
        raise HTTPException(status_code=503, detail="Office document conversion is temporarily unavailable on this server.")
    raise HTTPException(status_code=400, detail=GENERIC_FAILURE)


# --------------------------------------------------------------------------- #
# File helpers
# --------------------------------------------------------------------------- #

FILE_ID_RE = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{2,5}$")


def cleanup_file(path: str) -> None:
    if path and os.path.exists(path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
        except Exception as e:
            log.warning("Error cleaning up %s: %s", path, e)


def purge_old_files(max_age: int = FILE_TTL_SECONDS) -> int:
    """Delete everything in TEMP_DIR older than max_age seconds. Returns number removed."""
    removed = 0
    cutoff = time.time() - max_age
    try:
        entries = list(os.scandir(TEMP_DIR))
    except FileNotFoundError:
        return 0
    for entry in entries:
        try:
            if entry.stat().st_mtime < cutoff:
                cleanup_file(entry.path)
                removed += 1
        except FileNotFoundError:
            continue
        except Exception as e:
            log.warning("Sweep error on %s: %s", entry.path, e)
    return removed


async def sweeper():
    while True:
        try:
            await asyncio.to_thread(purge_old_files)
        except Exception:
            log.exception("Temp sweep failed")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)


def safe_stem(filename) -> str:
    name = os.path.basename((filename or "").replace("\\", "/"))
    stem = os.path.splitext(name)[0]
    stem = re.sub(r"[^\w\-. ()]", "_", stem, flags=re.UNICODE).strip(" .")
    return stem[:100] or "converted"


def safe_download_name(filename: str) -> str:
    name = os.path.basename((filename or "").replace("\\", "/"))
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"[^\w\-. ()]", "_", stem, flags=re.UNICODE).strip(" .")[:100] or "converted"
    ext = re.sub(r"[^A-Za-z0-9.]", "", ext)[:8]
    return f"{stem}{ext}"


def save_upload(file: UploadFile, suffix: str) -> str:
    """Stream the upload to a UUID-named temp file, enforcing MAX_UPLOAD_BYTES while reading."""
    path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{suffix}")
    total = 0
    try:
        with open(path, "wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail=too_large_message())
                out.write(chunk)
    except BaseException:
        cleanup_file(path)
        raise
    if total == 0:
        cleanup_file(path)
        raise HTTPException(status_code=400, detail="The uploaded file is empty. Please choose a different file.")
    return path


def new_output(ext: str):
    file_id = f"{uuid.uuid4().hex}.{ext}"
    return file_id, os.path.join(TEMP_DIR, file_id)


@contextmanager
def conversion(out_path: str, *inputs: str, heavy: bool = False):
    """Run a conversion: optional concurrency limit, uniform error mapping, input cleanup."""
    slot = CONVERSION_SLOTS if heavy else nullcontext()
    try:
        with slot:
            yield
    except HTTPException:
        cleanup_file(out_path)
        raise
    except Exception:
        log.exception("Conversion failed")
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=GENERIC_FAILURE)
    finally:
        for p in inputs:
            cleanup_file(p)


def flatten_to_rgb(image: Image.Image) -> Image.Image:
    """Convert to RGB, compositing transparency onto white (JPEG/PDF have no alpha)."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])
        return bg
    return image.convert("RGB")


# --------------------------------------------------------------------------- #
# Rate limiting + upload-size guard (pure ASGI middleware, runs before body parsing)
# --------------------------------------------------------------------------- #

class RateLimiter:
    """Sliding-window, in-memory, per-key limiter."""

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.hits = {}

    def check(self, key: str) -> int:
        """Return 0 if allowed (and record the hit), else seconds until retry."""
        if self.limit <= 0:
            return 0
        now = time.monotonic()
        q = self.hits.setdefault(key, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return max(1, int(self.window - (now - q[0])) + 1)
        q.append(now)
        if len(self.hits) > 5000:
            for k in [k for k, v in self.hits.items() if not v or now - v[-1] >= self.window]:
                self.hits.pop(k, None)
        return 0


rate_limiter = RateLimiter(RATE_LIMIT_MAX, RATE_LIMIT_WINDOW)


class _BodyTooLarge(Exception):
    pass


def client_ip(scope) -> str:
    headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
    if TRUST_PROXY:
        for h in ("cf-connecting-ip", "true-client-ip"):
            if headers.get(h):
                return headers[h].strip()
        xff = headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


class UploadGuardMiddleware:
    """For POST /api/convert/*: per-IP rate limit, then reject oversized bodies early with HTTP 413."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (scope["type"] != "http" or scope["method"] != "POST"
                or not scope["path"].startswith("/api/convert/")):
            await self.app(scope, receive, send)
            return

        retry_after = rate_limiter.check(client_ip(scope))
        if retry_after:
            minutes = max(1, round(RATE_LIMIT_WINDOW / 60))
            resp = JSONResponse(
                {"detail": f"Too many conversions. Free use is limited to {RATE_LIMIT_MAX} conversions "
                           f"per {minutes} minutes. Please wait about {max(1, round(retry_after / 60))} "
                           "minute(s) and try again."},
                status_code=429, headers={"Retry-After": str(retry_after)})
            await resp(scope, receive, send)
            return

        limit = MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD
        headers = dict(scope.get("headers", []))
        cl = headers.get(b"content-length")
        if cl and cl.isdigit() and int(cl) > limit:
            # Drain (bounded) so browsers can read the 413 instead of seeing a connection reset.
            if int(cl) <= DRAIN_CAP_BYTES:
                remaining = int(cl)
                while remaining > 0:
                    msg = await receive()
                    if msg["type"] != "http.request":
                        break
                    remaining -= len(msg.get("body", b""))
                    if not msg.get("more_body", False):
                        break
            resp = JSONResponse({"detail": too_large_message()}, status_code=413)
            await resp(scope, receive, send)
            return

        received = 0
        started = False

        async def limited_receive():
            nonlocal received
            msg = await receive()
            if msg["type"] == "http.request":
                received += len(msg.get("body", b""))
                if received > limit:
                    raise _BodyTooLarge()
            return msg

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not started:
                resp = JSONResponse({"detail": too_large_message()}, status_code=413)
                await resp(scope, receive, tracking_send)


class TrailingSlashRedirectMiddleware:
    """One-hop 301 from `/path/` to the canonical `SITE_URL/path` (Starlette's default is a 307).

    Search Console reports 307s as temporary redirects; a single permanent hop to the absolute
    canonical URL consolidates signals and avoids http->https->no-slash chains.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] in ("GET", "HEAD"):
            path = scope["path"]
            if len(path) > 1 and path.endswith("/") and not path.startswith(("/static/", "/api/")):
                target = "/" + path.strip("/")
                # Collapse leading slashes so `//evil.com/` can never become a protocol-relative URL.
                target = re.sub(r"/{2,}", "/", target)
                # scope["path"] is percent-decoded: re-encode so CR/LF, '?' and non-Latin-1 chars
                # can't break or alter the Location header.
                target = urllib.parse.quote(target, safe="/:@!$&'()*+,;=-._~")
                qs = scope.get("query_string", b"").decode("latin-1")
                location = SITE_URL + target + (f"?{qs}" if qs else "")
                resp = Response(status_code=301, headers={"Location": location})
                await resp(scope, receive, send)
                return
        await self.app(scope, receive, send)


class SecurityHeadersMiddleware:
    """Baseline hardening headers on every response (clickjacking, MIME sniffing, HTTPS, referrer leaks).

    No Content-Security-Policy on purpose: AdSense Auto Ads + GA4 load scripts/frames from a large,
    changing set of Google domains, and a strict CSP silently breaks ad serving (= lost revenue).
    """

    HEADERS = [
        (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"SAMEORIGIN"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=(), usb=()"),
    ]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                existing = {k.lower() for k, _ in message.get("headers", [])}
                message["headers"] = list(message.get("headers", [])) + [
                    (k, v) for k, v in self.HEADERS if k not in existing]
            await send(message)

        await self.app(scope, receive, send_with_headers)


# --------------------------------------------------------------------------- #
# App + templates
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(sweeper())
    log.info("ffmpeg=%s soffice=%s max_upload=%sMB rate=%s/%ss",
             FFMPEG_PATH, SOFFICE_PATH, MAX_UPLOAD_MB, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW)
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="PureFileConverter", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(UploadGuardMiddleware)
app.add_middleware(TrailingSlashRedirectMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

class CachedStaticFiles(StaticFiles):
    """StaticFiles with long-lived Cache-Control headers for SEO/performance."""
    async def get_response(self, path: str, scope):
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp

app.mount("/static", CachedStaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=BASE_DIR)
try:  # cache-buster: CSS is served "immutable", so the URL must change whenever the file does
    ASSET_VERSION = str(int(os.path.getmtime(os.path.join(STATIC_DIR, "tailwind.css"))))
except OSError:
    ASSET_VERSION = "1"
templates.env.globals.update(
    site_url=SITE_URL,
    asset_version=ASSET_VERSION,
    contact_email=CONTACT_EMAIL,
    max_upload_mb=f"{MAX_UPLOAD_MB:g}",
    adsense_client_id=ADSENSE_CLIENT_ID,
    legal_updated=LEGAL_UPDATED,
    current_year=datetime.now(timezone.utc).year,
    file_ttl_label="1 hour",
)


def render(request: Request, name: str, status_code: int = 200, **ctx):
    return templates.TemplateResponse(request=request, name=name, context=ctx, status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    path = request.url.path
    if exc.status_code == 404 and not path.startswith("/api/") and "text/html" in request.headers.get("accept", ""):
        return render(request, "error.html", status_code=404, noindex=True,
                      page_title="Page not found | PureFileConverter",
                      page_description="The page you are looking for does not exist.",
                      heading="Page not found",
                      message="We couldn't find that page, or the download link has expired.")
    return await default_http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "detail": "Invalid or missing input. Please choose a file, check any options (such as width, "
                  "height or quality) and try again."})


# --------------------------------------------------------------------------- #
# Tool catalogue
# --------------------------------------------------------------------------- #

COLOR_CLASSES = {  # literal class names so the Tailwind build can see them
    "red": "bg-red-100 text-red-600",
    "blue": "bg-blue-100 text-blue-600",
    "green": "bg-green-100 text-green-600",
    "emerald": "bg-emerald-100 text-emerald-600",
    "yellow": "bg-yellow-100 text-yellow-600",
    "orange": "bg-orange-100 text-orange-600",
    "teal": "bg-teal-100 text-teal-600",
    "cyan": "bg-cyan-100 text-cyan-600",
    "purple": "bg-purple-100 text-purple-600",
    "indigo": "bg-indigo-100 text-indigo-600",
    "fuchsia": "bg-fuchsia-100 text-fuchsia-600",
    "pink": "bg-pink-100 text-pink-600",
}

CATEGORIES = [
    {"name": "Document Tools", "heading": "text-blue-700 border-blue-200", "badge": "bg-blue-100 text-blue-600"},
    {"name": "PDF Tools", "heading": "text-red-700 border-red-200", "badge": "bg-red-100 text-red-600"},
    {"name": "Image Tools", "heading": "text-green-700 border-green-200", "badge": "bg-green-100 text-green-600"},
    {"name": "Media Tools", "heading": "text-purple-700 border-purple-200", "badge": "bg-purple-100 text-purple-600"},
]

TOOLS_CONFIG = {
    "pdf-to-word": {
        "category": "Document Tools",
        "title": "PDF to Word",
        "accept": ".pdf",
        "description": "Easily convert your PDF files into easy to edit DOCX documents.",
        "intro": "Turn a PDF into an editable Word (.docx) document. Text, tables and images are carried over so you can edit the content in Microsoft Word, Google Docs or LibreOffice.",
        "faq": ("Will it work on scanned PDFs?", "Only PDFs that contain real, selectable text convert into editable text. Scanned pages that are just pictures are converted as images because we do not run OCR."),
        "endpoint": "/api/convert/pdf-to-word",
        "has_format_selector": False,
        "icon": "fa-file-pdf",
        "color": "red",
    },
    "word-to-pdf": {
        "category": "Document Tools",
        "title": "Word to PDF",
        "accept": ".doc,.docx",
        "description": "Make DOC and DOCX files easy to read by converting them to PDF.",
        "intro": "Convert Word documents to PDF so they look the same on every device. Both the older .doc and the modern .docx formats are supported.",
        "faq": ("Which Word formats are supported?", "Both .doc and .docx files. Fonts that are not installed on our server are replaced with similar ones, so complex layouts can shift slightly."),
        "endpoint": "/api/convert/word-to-pdf",
        "has_format_selector": False,
        "icon": "fa-file-word",
        "color": "blue",
    },
    "csv-to-excel": {
        "category": "Document Tools",
        "title": "CSV to Excel",
        "accept": ".csv",
        "description": "Convert CSV files to XLSX easily and accurately.",
        "intro": "Convert comma-separated (.csv) files into a clean Excel workbook (.xlsx) that opens directly in Excel, Google Sheets and LibreOffice Calc.",
        "faq": ("What kind of CSV files work best?", "Comma-separated files with a header row, saved as UTF-8 (Latin-1 is also detected). The first row becomes the column headings."),
        "endpoint": "/api/convert/csv-to-excel",
        "has_format_selector": False,
        "icon": "fa-file-csv",
        "color": "green",
    },
    "excel-to-pdf": {
        "category": "Document Tools",
        "title": "Excel to PDF",
        "accept": ".xls,.xlsx,.csv",
        "description": "Convert Excel spreadsheets to PDF format.",
        "intro": "Convert Excel spreadsheets (.xls, .xlsx) or CSV files into a print-ready PDF that is easy to share and read.",
        "faq": ("Why does my wide spreadsheet span several pages?", "Each sheet is printed using its own page setup. Very wide sheets may split across pages; set the print area or 'fit to width' in Excel before converting for the best result."),
        "endpoint": "/api/convert/excel-to-pdf",
        "has_format_selector": False,
        "icon": "fa-file-excel",
        "color": "emerald",
    },
    "pdf-to-jpg": {
        "category": "Document Tools",
        "title": "PDF to JPG",
        "accept": ".pdf,application/pdf",
        "description": "Turn every page of a PDF into a high-quality JPG image.",
        "intro": "Convert PDF pages into sharp JPG images at 150 DPI. A one-page PDF downloads as a single JPG; a multi-page PDF downloads as a ZIP with one JPG per page (up to 50 pages).",
        "faq": ("What happens with multi-page PDFs?", "Each page becomes its own JPG image at 150 DPI. Single-page PDFs download as one .jpg file; PDFs with 2 to 50 pages download as a .zip containing page-1.jpg, page-2.jpg and so on."),
        "endpoint": "/api/convert/pdf-to-jpg",
        "has_format_selector": False,
        "icon": "fa-file-image",
        "color": "red",
    },
    "image-converter": {
        "category": "Image Tools",
        "title": "Image Converter",
        "accept": "image/png, image/jpeg, image/webp",
        "description": "Convert JPG, PNG, and WebP images to your desired format.",
        "intro": "Convert images between JPG, PNG and WebP. Choose the output format, upload your picture and download the converted file in seconds.",
        "faq": ("What happens to transparent backgrounds?", "PNG and WebP keep transparency. JPG cannot store transparency, so transparent areas are filled with white when you convert to JPG."),
        "endpoint": "/api/convert/image",
        "has_format_selector": True,
        "icon": "fa-image",
        "color": "yellow",
    },
    "image-to-pdf": {
        "category": "Image Tools",
        "title": "Image to PDF",
        "accept": "image/png, image/jpeg, image/webp",
        "description": "Convert images into PDF documents.",
        "intro": "Turn a JPG, PNG or WebP image into a PDF document that is easy to print, email or archive.",
        "faq": ("Can I combine several images into one PDF?", "Not yet. Each upload creates a single-page PDF from one image."),
        "endpoint": "/api/convert/image-to-pdf",
        "has_format_selector": False,
        "icon": "fa-file-image",
        "color": "orange",
    },
    "image-resizer": {
        "category": "Image Tools",
        "title": "Image Resizer",
        "accept": "image/png, image/jpeg, image/webp",
        "description": "Resize your images to specific dimensions.",
        "intro": "Resize a JPG, PNG or WebP image to an exact width and height in pixels, ready for social media, websites or email.",
        "faq": ("Is the aspect ratio kept?", "The image is resized to exactly the width and height you enter (1-8000 pixels). To avoid stretching, enter values that keep the original proportions."),
        "endpoint": "/api/convert/image-resizer",
        "has_format_selector": False,
        "has_resize_inputs": True,
        "icon": "fa-down-left-and-up-right-to-center",
        "color": "teal",
    },
    "compress-image": {
        "category": "Image Tools",
        "title": "Compress Image",
        "accept": "image/jpeg, image/webp",
        "description": "Compress images to reduce file size.",
        "intro": "Reduce the file size of JPG and WebP images by lowering the quality setting. Smaller images load faster and are easier to share.",
        "faq": ("What quality setting should I use?", "Values between 60 and 80 usually give a big size reduction with little visible loss. Lower values make smaller files but look more compressed."),
        "endpoint": "/api/convert/compress-image",
        "has_format_selector": False,
        "has_quality_input": True,
        "icon": "fa-compress",
        "color": "cyan",
    },
    "heic-to-jpg": {
        "category": "Image Tools",
        "title": "HEIC to JPG",
        "accept": ".heic,.heif,image/heic,image/heif",
        "description": "Convert iPhone HEIC photos into universally compatible JPG images.",
        "intro": "iPhones save photos as HEIC, which many Windows PCs, websites and apps cannot open. Upload a HEIC or HEIF photo and download a standard JPG that works everywhere.",
        "faq": ("Will my photo lose quality?", "The JPG is saved at high quality (92) with the original resolution and correct orientation, so the difference is not visible for normal viewing, printing or sharing."),
        "endpoint": "/api/convert/heic-to-jpg",
        "has_format_selector": False,
        "icon": "fa-mobile-screen-button",
        "color": "orange",
    },
    "remove-background": {
        "category": "Image Tools",
        "title": "Remove Background",
        "seo_title": "Remove Background from Image Free – AI, No Upload",
        "meta": "Remove the background from any photo free with AI. Get a transparent PNG in seconds — "
                "runs in your browser, no upload, no signup, no watermark.",
        "accept": "image/png, image/jpeg, image/webp",
        "description": "Erase photo backgrounds with AI and download a transparent PNG.",
        "intro": "Remove the background from product photos, portraits, logos and selfies in one click. The AI model runs entirely inside your web browser, so your photo is never uploaded to any server. You get a full-resolution transparent PNG (up to 2048 px) that is ready for online stores, profile pictures, presentations and design projects.",
        "faq": ("Is my photo uploaded to your server?", "No. The AI runs 100% in your browser using WebAssembly, so your photo never leaves your device. The first use downloads the AI model (about 44 MB) once; after that it is cached and works much faster."),
        "faqs": [
            ("Is the background remover really free?",
             "Yes. It is completely free with no signup, no watermark and no credits. You download a full-quality transparent PNG every time."),
            ("Is my photo uploaded to your server?",
             "No. The AI runs 100% in your browser using WebAssembly, so your photo never leaves your device. The first use downloads the AI model (about 44 MB) once; after that it is cached and works much faster."),
            ("Which images work best?",
             "Photos with a clear main subject, such as a person, product, pet, car or logo, give the cleanest edges. JPG, PNG and WebP up to 25 MB are supported; very large photos are scaled to 2048 px on the longest side."),
            ("Why is the first run slower?",
             "Your browser downloads and prepares the AI model on the first run, which can take 10 to 60 seconds depending on your connection. Later photos are processed in a few seconds."),
        ],
        "client_side": "remove-background",
        "endpoint": "",
        "has_format_selector": False,
        "icon": "fa-wand-magic-sparkles",
        "color": "emerald",
    },
    "qr-code-generator": {
        "category": "Image Tools",
        "title": "QR Code Generator",
        "seo_title": "Free QR Code Generator – No Signup, Never Expires",
        "meta": "Create a free QR code for any link, text, email or phone number. High-resolution PNG, "
                "no watermark, no signup, and it never expires.",
        "accept": "",
        "description": "Turn any link or text into a high-resolution QR code image.",
        "intro": "Create a QR code for a website link, menu, business card, flyer, Wi-Fi details or any text. Paste your content, click Generate and download a crisp, print-ready PNG of about 1000 x 1000 pixels. The code is static, so it works forever: no account, no tracking redirects and no expiry date.",
        "faq": ("Will my QR code ever stop working?", "No. The QR code stores your link or text directly inside the image, with no redirect service in between, so it keeps working forever and cannot be switched off."),
        "faqs": [
            ("Is the QR code generator really free?",
             "Yes. Create as many QR codes as you like for free, with no signup, no watermark and no limits on scans."),
            ("Will my QR code ever stop working?",
             "No. The QR code stores your link or text directly inside the image, with no redirect service in between, so it keeps working forever and cannot be switched off."),
            ("What can I put in a QR code?",
             "Website links, plain text, email addresses, phone numbers or Wi-Fi details, up to 1000 characters. For Wi-Fi, use the format WIFI:T:WPA;S:NetworkName;P:Password;; and phones will offer to join the network."),
            ("Can I print the QR code?",
             "Yes. The PNG is about 1000 x 1000 pixels with a quiet-zone border and medium error correction, which prints sharply on flyers, menus, posters and business cards."),
        ],
        "client_side": "qr",
        "endpoint": "/api/convert/qr-code-generator",
        "has_format_selector": False,
        "icon": "fa-qrcode",
        "color": "teal",
    },
    "mp4-to-mp3": {
        "category": "Media Tools",
        "title": "MP4 to MP3",
        "accept": ".mp4",
        "description": "Extract audio from MP4 video files and save as MP3.",
        "intro": "Extract the audio track from an MP4 video and save it as an MP3 file you can play anywhere.",
        "faq": ("Why do I get a 'no audio track' error?", "Some MP4 files, such as screen recordings, have no sound. The converter can only extract audio that exists in the video."),
        "endpoint": "/api/convert/mp4-to-mp3",
        "has_format_selector": False,
        "icon": "fa-file-audio",
        "color": "purple",
    },
    "wav-to-mp3": {
        "category": "Media Tools",
        "title": "WAV to MP3",
        "accept": ".wav",
        "description": "Convert WAV audio files to MP3 format.",
        "intro": "Convert large, uncompressed WAV recordings into compact MP3 files that are easier to store and share.",
        "faq": ("Will the audio quality change?", "MP3 is a compressed format, so a small amount of audio detail is lost in exchange for a much smaller file."),
        "endpoint": "/api/convert/wav-to-mp3",
        "has_format_selector": False,
        "icon": "fa-music",
        "color": "indigo",
    },
    "avi-to-mp4": {
        "category": "Media Tools",
        "title": "AVI to MP4",
        "accept": ".avi",
        "description": "Convert AVI video files to MP4 format.",
        "intro": "Convert AVI videos to MP4 (H.264 video with AAC audio), the format that plays on phones, browsers and most devices.",
        "faq": ("How long does a video conversion take?", "Usually from a few seconds to a couple of minutes, depending on the video length and how busy the server is."),
        "endpoint": "/api/convert/avi-to-mp4",
        "has_format_selector": False,
        "icon": "fa-file-video",
        "color": "fuchsia",
    },
    "mp3-to-mp4": {
        "category": "Media Tools",
        "title": "MP3 to MP4",
        "accept": ".mp3",
        "description": "Create a static video from an MP3 audio file.",
        "intro": "Turn an MP3 audio file into an MP4 video with a plain black screen, handy for uploading audio to platforms that only accept video.",
        "faq": ("What does the video show?", "A simple black 640x480 screen with your audio playing over it. Custom cover art is not supported yet."),
        "endpoint": "/api/convert/mp3-to-mp4",
        "has_format_selector": False,
        "icon": "fa-film",
        "color": "pink",
    },
    "mp4-to-gif": {
        "category": "Media Tools",
        "title": "MP4 to GIF",
        "accept": ".mp4,.mov,.webm,video/mp4",
        "description": "Turn a short video clip into an animated GIF.",
        "intro": "Convert the first 15 seconds of an MP4, MOV or WebM clip into a smooth looping GIF (12 fps, up to 480 px wide) using an optimized colour palette, ready for chats, social media and memes.",
        "faq": ("Is there a length limit?", "GIFs grow large very quickly, so the converter uses the first 15 seconds of the clip at 12 frames per second and up to 480 pixels wide. Trim your video first if you need a different section."),
        "endpoint": "/api/convert/mp4-to-gif",
        "has_format_selector": False,
        "icon": "fa-photo-film",
        "color": "fuchsia",
    },
    "gif-to-mp4": {
        "category": "Media Tools",
        "title": "GIF to MP4",
        "accept": ".gif,image/gif",
        "description": "Convert animated GIFs into small, smooth MP4 videos.",
        "intro": "Convert an animated GIF into an MP4 video that is often 5 to 10 times smaller and plays smoothly on Instagram, TikTok, X, WhatsApp, PowerPoint and every phone. The video uses H.264, the most compatible format, keeps the original frame rate and covers the first 30 seconds at up to 720 pixels.",
        "faq": ("Why convert a GIF to MP4?", "MP4 video compresses animation far better than GIF, so files are usually 5 to 10 times smaller with smoother colours. Many social networks and messaging apps also accept MP4 where large GIFs fail to upload."),
        "endpoint": "/api/convert/gif-to-mp4",
        "has_format_selector": False,
        "icon": "fa-clapperboard",
        "color": "indigo",
    },
    "merge-pdf": {
        "category": "PDF Tools",
        "title": "Merge PDF",
        "seo_title": "Merge PDF Online Free – Combine PDF Files",
        "meta": "Merge PDF files online for free. Combine up to 10 PDFs into one document in seconds — "
                "no signup, no watermark, files deleted after 1 hour.",
        "accept": ".pdf,application/pdf",
        "description": "Combine multiple PDF files into one document in the order you choose.",
        "intro": "Merge PDF files into a single document in seconds. Select 2 to 10 PDFs, and they are joined in the order you pick them, keeping every page, link and bookmark-free layout intact. Perfect for combining scanned pages, invoices, reports or job application documents into one file.",
        "faq": ("In what order are the PDFs merged?", "Files are combined in the order you select them. Tip: name your files 1, 2, 3 before uploading so your file picker lists them in the right order. Up to 10 PDFs and 10 MB total per merge."),
        "endpoint": "/api/convert/merge-pdf",
        "has_format_selector": False,
        "multi_file": True,
        "icon": "fa-object-group",
        "color": "red",
    },
    "split-pdf": {
        "category": "PDF Tools",
        "title": "Split PDF",
        "seo_title": "Split PDF Online Free – Extract PDF Pages",
        "meta": "Split a PDF online for free. Extract specific pages or save every page as a separate PDF — "
                "no signup, no watermark, files deleted after 1 hour.",
        "accept": ".pdf,application/pdf",
        "description": "Extract pages from a PDF or split every page into its own file.",
        "intro": "Split a PDF into separate files or pull out just the pages you need. Leave the page box empty to save every page as its own PDF (downloaded as a ZIP), or type pages like 1-3, 5 to extract them into one new PDF.",
        "faq": ("How do I extract only certain pages?", "Type the pages you want in the page box, for example 2 for a single page, 1-3 for a range, or 1-3, 7, 10-12 for a mix. Those pages are saved, in that order, into one new PDF. Leave the box empty to split every page into its own file."),
        "endpoint": "/api/convert/split-pdf",
        "has_format_selector": False,
        "has_pages_input": True,
        "icon": "fa-scissors",
        "color": "orange",
    },
    "compress-pdf": {
        "category": "PDF Tools",
        "title": "Compress PDF",
        "seo_title": "Compress PDF Online Free – Reduce PDF Size",
        "meta": "Compress PDF files online for free. Reduce PDF file size for email and uploads while keeping "
                "it readable — no signup, no watermark, auto-deleted.",
        "accept": ".pdf,application/pdf",
        "description": "Reduce PDF file size for email, uploads and sharing.",
        "intro": "Make large PDFs smaller so they fit email attachment limits and upload forms. The compressor shrinks oversized images, recompresses page content and removes duplicate data, while keeping text sharp and searchable. Your PDF is never made larger than the original.",
        "faq": ("How much smaller will my PDF get?", "Scanned and image-heavy PDFs often shrink by 50 to 90 percent. PDFs that are mostly text are already compact, so the savings are smaller. If compression cannot make your file smaller, you get the original back unchanged."),
        "endpoint": "/api/convert/compress-pdf",
        "has_format_selector": False,
        "icon": "fa-file-zipper",
        "color": "emerald",
    },
    "rotate-pdf": {
        "category": "PDF Tools",
        "title": "Rotate PDF",
        "seo_title": "Rotate PDF Online Free – Rotate PDF Pages",
        "meta": "Rotate PDF pages online for free. Turn every page 90°, 180° or 270° and save a fixed PDF — "
                "no signup, no watermark, files deleted after 1 hour.",
        "accept": ".pdf,application/pdf",
        "description": "Rotate all pages of a PDF 90°, 180° or 270° and save it permanently.",
        "intro": "Fix sideways or upside-down PDFs permanently. Choose 90° clockwise, 180° or 270° and every page is rotated and saved, so the document opens the right way up on any device, printer or viewer.",
        "faq": ("Is the rotation permanent?", "Yes. The rotation is saved into the new PDF file, so it opens correctly in Adobe Reader, Chrome, Edge, Preview, phones and printers. The page content itself is not re-rendered, so quality is unchanged."),
        "endpoint": "/api/convert/rotate-pdf",
        "has_format_selector": False,
        "has_angle_select": True,
        "icon": "fa-rotate",
        "color": "blue",
    },
}

# Clean SEO titles for tools whose name is not an "X to Y" conversion.
TOOLS_CONFIG["image-converter"]["seo_title"] = "Image Converter Online Free – JPG, PNG & WebP"
TOOLS_CONFIG["image-resizer"]["seo_title"] = "Image Resizer Online Free – Resize JPG, PNG, WebP"
TOOLS_CONFIG["compress-image"]["seo_title"] = "Compress Image Online Free – Reduce Image Size"

for _slug, _tool in TOOLS_CONFIG.items():
    _tool["slug"] = _slug
    _tool["badge"] = COLOR_CLASSES[_tool["color"]]

TOOLS_BY_CATEGORY = [
    {**cat, "tools": [t for t in TOOLS_CONFIG.values() if t["category"] == cat["name"]]}
    for cat in CATEGORIES
]
templates.env.globals["tools_by_category"] = TOOLS_BY_CATEGORY
templates.env.globals["tools_count"] = len(TOOLS_CONFIG)

LEGAL_PAGES = ["privacy", "terms", "contact", "about"]

# --------------------------------------------------------------------------- #
# Blog
# --------------------------------------------------------------------------- #

from blog_data import BLOG_ARTICLES, BLOG_CATEGORIES
from blog_redirects import REMOVED_ARTICLE_REDIRECTS
from tool_content import TOOL_GUIDES

HOME_GUIDES = [  # guides linked from the homepage "Popular guides" box
    "how-to-convert-pdf-to-word", "how-to-compress-pdf-files", "how-to-convert-heic-to-jpg",
    "jpg-vs-png-vs-webp-guide", "how-to-extract-audio-from-mp4", "is-it-safe-to-convert-files-online",
]

for _slug, _guide in TOOL_GUIDES.items():  # long-form, tool-specific help rendered under each converter
    _article = _guide.get("article")
    TOOLS_CONFIG[_slug]["guide"] = {**_guide, "article_title": BLOG_ARTICLES[_article]["title"] if _article else None}

def blog_article_jsonld(article: dict) -> list:
    url = f"{SITE_URL}/blog/{article['slug']}"
    image = next((b["src"] for b in article["content_blocks"] if b["type"] == "image"), "/static/og-image.png")
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["title"],
        "description": article["description"],
        "url": url,
        "image": SITE_URL + image,
        "datePublished": article["date_published"],
        "dateModified": article["date_modified"],
        "author": {
            "@type": "Person",
            "name": "Omy Grace",
            "url": SITE_URL + "/about",
        },
        "publisher": {
            "@type": "Organization",
            "name": "PureFileConverter",
            "logo": {"@type": "ImageObject", "url": SITE_URL + "/static/og-image.svg"},
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
    }
    return [jsonld_dumps(article_schema)]


def build_faqs(tool: dict):
    if tool.get("faqs"):  # tools that do not upload a file (browser AI, text input) need their own answers
        return list(tool["faqs"])
    title = tool["title"]
    return [
        (f"Is the {title} converter really free?",
         f"Yes. PureFileConverter is free to use with no signup and no watermarks. The only limits are a "
         f"{MAX_UPLOAD_MB:g} MB maximum file size and a fair-use cap on the number of conversions per hour."),
        ("Are my files private?",
         "Files are uploaded over HTTPS, converted on our server and automatically deleted after 1 hour at the "
         "latest (or right after you download the result). We do not share or sell your files."),
        ("What is the maximum file size?", f"The maximum upload size is {MAX_UPLOAD_MB:g} MB per file."),
        tool["faq"],
    ]


def jsonld_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def tool_jsonld(tool: dict, faqs):
    url = f"{SITE_URL}/{tool['slug']}"
    webapp = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": f"{tool['title']} - PureFileConverter",
        "url": url,
        "description": f"{tool['description']} Free online converter, no signup.",
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": "Any (web browser)",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    }
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs
        ],
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "PureFileConverter", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": tool["title"], "item": url},
        ],
    }
    return [jsonld_dumps(webapp), jsonld_dumps(faq), jsonld_dumps(breadcrumb)]


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #

def _page(path: str):
    return app.api_route(path, methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)


@_page("/")
async def read_index(request: Request):
    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "PureFileConverter",
        "url": SITE_URL + "/",
        "description": "Free online file converter for documents, images, audio and video.",
        "potentialAction": {
            "@type": "SearchAction",
            "target": SITE_URL + "/?q={search_term_string}",
            "query-input": "required name=search_term_string",
        },
    }
    org = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "PureFileConverter",
        "url": SITE_URL,
        "logo": SITE_URL + "/static/og-image.svg",
        "description": "Free online file converter and PDF tools for documents, images, audio and video. "
                       "No signup, no watermarks.",
        "knowsAbout": [
            "File conversion", "PDF conversion", "PDF merging", "PDF splitting", "PDF compression",
            "Document conversion", "Image processing", "HEIC to JPG conversion", "AI background removal",
            "QR code generation", "Audio extraction", "Video transcoding", "GIF to MP4 conversion",
            "Online converter tools",
        ],
        "sameAs": [
            "https://github.com/omareg03/purefileconverter",
            "https://www.saashub.com/purefileconverter",
        ],
    }
    return render(
        request, "index.html",
        page_title="Free Online File Converter & PDF Tools | PureFileConverter",
        page_description=f"Free online file converter and PDF tools: merge, split and compress PDF, PDF to Word, "
                         f"HEIC to JPG, MP4 to MP3 and more — {len(TOOLS_CONFIG)} tools, no signup, no watermark.",
        jsonld_blocks=[jsonld_dumps(website), jsonld_dumps(org)],
        home_guides=[BLOG_ARTICLES[s] for s in HOME_GUIDES],
        guides_count=len(BLOG_ARTICLES),
    )


@_page("/privacy")
async def privacy(request: Request):
    return render(request, "privacy.html", page_title="Privacy Policy | PureFileConverter",
                  page_description="How PureFileConverter handles your files, cookies and advertising. "
                                   "Files are automatically deleted after 1 hour; no account is required.")


@_page("/terms")
async def terms(request: Request):
    return render(request, "terms.html", page_title="Terms of Service | PureFileConverter",
                  page_description="The terms for using PureFileConverter, a free online file conversion service.")


@_page("/contact")
async def contact(request: Request):
    return render(request, "contact.html", page_title="Contact Us | PureFileConverter",
                  page_description="Contact PureFileConverter for support, feedback or business enquiries.")


@_page("/about")
async def about(request: Request):
    return render(request, "about.html", page_title="About PureFileConverter",
                  page_description="PureFileConverter is a free, no-signup online file converter for documents, "
                                   "images, audio and video.")


@_page("/download-page")
async def download_page(request: Request, file_id: str, filename: str):
    if not FILE_ID_RE.match(file_id) or not os.path.exists(os.path.join(TEMP_DIR, file_id)):
        raise HTTPException(status_code=404, detail="File not found or already downloaded.")
    return render(request, "download.html", file_id=file_id, filename=safe_download_name(filename),
                  noindex=True, page_title="Download Ready | PureFileConverter",
                  page_description="Your converted file is ready to download.")


@app.get("/api/download/{file_id}")
async def download_file(file_id: str, filename: str = "converted"):
    if not FILE_ID_RE.match(file_id):
        raise HTTPException(status_code=404, detail="File not found or already downloaded.")
    file_path = os.path.join(TEMP_DIR, file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found or already downloaded.")
    return FileResponse(path=file_path, filename=safe_download_name(filename),
                        background=BackgroundTask(cleanup_file, file_path))


# --------------------------------------------------------------------------- #
# Operational / SEO endpoints
# --------------------------------------------------------------------------- #

@app.api_route("/health", methods=["GET", "HEAD"], include_in_schema=False)
def health():
    return {"status": "ok", "ffmpeg": bool(FFMPEG_PATH), "libreoffice": bool(SOFFICE_PATH)}


@app.api_route("/robots.txt", methods=["GET", "HEAD"], include_in_schema=False)
def robots_txt():
    body = (
        # Default: allow all crawlers to access everything except API + download
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /download-page\n"
        "\n"
        # Explicitly welcome AI search/retrieval bots (cited in ChatGPT, Perplexity, Claude, Google AI)
        "User-agent: GPTBot\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: OAI-SearchBot\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: ChatGPT-User\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: PerplexityBot\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: Perplexity-User\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: ClaudeBot\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: Claude-SearchBot\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: Google-Extended\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: CCBot\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: Applebot-Extended\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "User-agent: anthropic-ai\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    return PlainTextResponse(body)


@app.api_route("/sitemap.xml", methods=["GET", "HEAD"], include_in_schema=False)
def sitemap_xml():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    paths = [("/", 1.0)] + [(f"/{slug}", 0.8) for slug in TOOLS_CONFIG] + [(f"/{p}", 0.3) for p in LEGAL_PAGES]
    paths.append(("/blog", 0.7))
    paths += [(f"/blog/{slug}", 0.6) for slug in BLOG_ARTICLES]
    urls = "".join(
        f"  <url><loc>{SITE_URL}{p}</loc><lastmod>{today}</lastmod><priority>{pr}</priority></url>\n"
        for p, pr in paths
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n')
    return Response(content=xml, media_type="application/xml")


@app.api_route("/ads.txt", methods=["GET", "HEAD"], include_in_schema=False)
def ads_txt():
    if not ADSENSE_CLIENT_ID:
        raise HTTPException(status_code=404, detail="Not found")
    pub = ADSENSE_CLIENT_ID.replace("ca-", "", 1)
    return PlainTextResponse(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")


# --------------------------------------------------------------------------- #
# llms.txt — AI crawler navigation file (community standard, like sitemap for LLMs)
# --------------------------------------------------------------------------- #

@app.api_route("/llms.txt", methods=["GET", "HEAD"], include_in_schema=False)
def llms_txt():
    """Plain-text Markdown file that tells AI crawlers what the site covers and
    which pages carry the most signal. Modeled on the answer.ai llms.txt spec."""
    tool_lines = "\n".join(
        f"- [{t['title']}]({SITE_URL}/{slug}): {t['description']}"
        for slug, t in TOOLS_CONFIG.items()
    )
    body = (
        f"# PureFileConverter\n\n"
        f"> Free online file converter for documents, images, audio and video. "
        f"No signup, no watermarks. Files are automatically deleted after 1 hour. "
        f"{len(TOOLS_CONFIG)} dedicated conversion tools and {len(BLOG_ARTICLES)} in-depth conversion guides.\n\n"
        f"## Document Tools\n"
        f"- [PDF to Word]({SITE_URL}/pdf-to-word): Convert PDF files into editable DOCX documents.\n"
        f"- [Word to PDF]({SITE_URL}/word-to-pdf): Convert DOC and DOCX files to PDF.\n"
        f"- [CSV to Excel]({SITE_URL}/csv-to-excel): Convert CSV files to styled XLSX workbooks.\n"
        f"- [Excel to PDF]({SITE_URL}/excel-to-pdf): Convert Excel spreadsheets to print-ready PDF.\n"
        f"- [PDF to JPG]({SITE_URL}/pdf-to-jpg): Convert every PDF page to a 150 DPI JPG image (ZIP for multi-page).\n\n"
        f"## PDF Tools\n"
        f"- [Merge PDF]({SITE_URL}/merge-pdf): Combine up to 10 PDF files into one document.\n"
        f"- [Split PDF]({SITE_URL}/split-pdf): Extract pages or split every page into its own PDF.\n"
        f"- [Compress PDF]({SITE_URL}/compress-pdf): Reduce PDF file size for email and uploads.\n"
        f"- [Rotate PDF]({SITE_URL}/rotate-pdf): Rotate all PDF pages 90, 180 or 270 degrees permanently.\n\n"
        f"## Image Tools\n"
        f"- [Image Converter]({SITE_URL}/image-converter): Convert between JPG, PNG and WebP.\n"
        f"- [Image to PDF]({SITE_URL}/image-to-pdf): Convert JPG, PNG, WebP images to PDF.\n"
        f"- [Image Resizer]({SITE_URL}/image-resizer): Resize images to exact dimensions.\n"
        f"- [Compress Image]({SITE_URL}/compress-image): Compress JPG and WebP images.\n"
        f"- [HEIC to JPG]({SITE_URL}/heic-to-jpg): Convert iPhone HEIC/HEIF photos to JPG.\n"
        f"- [Remove Background]({SITE_URL}/remove-background): Free AI background remover; runs in the browser (no upload) and exports a transparent PNG.\n"
        f"- [QR Code Generator]({SITE_URL}/qr-code-generator): Create static, never-expiring QR codes for links, text or Wi-Fi as a ~1000 px PNG.\n\n"
        f"## Media Tools\n"
        f"- [MP4 to MP3]({SITE_URL}/mp4-to-mp3): Extract audio from MP4 video.\n"
        f"- [WAV to MP3]({SITE_URL}/wav-to-mp3): Convert WAV audio to MP3.\n"
        f"- [AVI to MP4]({SITE_URL}/avi-to-mp4): Convert AVI video to MP4 (H.264).\n"
        f"- [MP3 to MP4]({SITE_URL}/mp3-to-mp4): Create a static video from an MP3 audio file.\n"
        f"- [MP4 to GIF]({SITE_URL}/mp4-to-gif): Turn a short video clip into an animated GIF.\n"
        f"- [GIF to MP4]({SITE_URL}/gif-to-mp4): Convert animated GIFs to small H.264 MP4 videos (first 30 s, up to 720 px).\n\n"
        f"## Blog & Guides\n"
        f"- [Blog]({SITE_URL}/blog): File conversion guides and tutorials.\n"
        + "".join(f"- [{a['title']}]({SITE_URL}/blog/{slug}): {a['description']}\n" for slug, a in BLOG_ARTICLES.items())
        + "\n"
        f"## Site Pages\n"
        f"- [About]({SITE_URL}/about): About PureFileConverter.\n"
        f"- [Privacy Policy]({SITE_URL}/privacy): How files are handled and deleted.\n"
        f"- [Terms of Service]({SITE_URL}/terms): Terms for using the free converter.\n"
        f"- [Contact]({SITE_URL}/contact): Contact PureFileConverter.\n\n"
        f"## Optional\n"
        f"- [Sitemap]({SITE_URL}/sitemap.xml): XML sitemap for search engines.\n"
    )
    return PlainTextResponse(body, media_type="text/plain")


FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<path d="M50 15 A35 35 0 0 1 85 50 L95 50 L80 70 L65 50 L75 50 A25 25 0 0 0 50 25 Z" fill="#2563eb"/>'
    '<path d="M50 85 A35 35 0 0 1 15 50 L5 50 L20 30 L35 50 L25 50 A25 25 0 0 0 50 75 Z" fill="#16a34a"/>'
    '</svg>'
)


@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


# --------------------------------------------------------------------------- #
# Conversion endpoints
# --------------------------------------------------------------------------- #

@app.post("/api/convert/csv-to-excel")
def convert_csv_to_excel(file: UploadFile = File(...)):
    src = save_upload(file, ".csv")
    file_id, out_path = new_output("xlsx")
    with conversion(out_path, src):
        try:
            try:
                df = pd.read_csv(src)
            except UnicodeDecodeError:
                df = pd.read_csv(src, encoding="latin-1")
        except pd.errors.EmptyDataError:
            raise HTTPException(status_code=400, detail="The CSV file is empty or has no columns.")
        df.to_excel(out_path, index=False)
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.xlsx"}


@app.post("/api/convert/pdf-to-word")
def convert_pdf_to_word(file: UploadFile = File(...)):
    src = save_upload(file, ".pdf")
    file_id, out_path = new_output("docx")
    with conversion(out_path, src, heavy=True):
        cv = Converter(src)
        try:
            cv.convert(out_path, start=0, end=None)
        finally:
            cv.close()
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.docx"}


@app.post("/api/convert/word-to-pdf")
def convert_word_to_pdf(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".doc", ".docx"):
        ext = ".docx"
    src = save_upload(file, ext)
    file_id, out_path = new_output("pdf")
    with conversion(out_path, src, heavy=True):
        office_to_pdf(src, out_path, com_word_to_pdf)
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.pdf"}


@app.post("/api/convert/excel-to-pdf")
def convert_excel_to_pdf(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".xls", ".xlsx", ".csv"):
        ext = ".xlsx"
    src = save_upload(file, ext)
    file_id, out_path = new_output("pdf")
    with conversion(out_path, src, heavy=True):
        office_to_pdf(src, out_path, com_excel_to_pdf)
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.pdf"}


IMAGE_FORMATS = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}


@app.post("/api/convert/image")
def convert_image(file: UploadFile = File(...), format: str = Form(...)):
    fmt = format.strip().lower()
    if fmt not in IMAGE_FORMATS:
        raise HTTPException(status_code=400, detail="Unsupported output format. Choose JPG, PNG or WebP.")
    pil_format = IMAGE_FORMATS[fmt]
    out_ext = "jpg" if pil_format == "JPEG" else fmt
    src = save_upload(file, ".img")
    file_id, out_path = new_output(out_ext)
    with conversion(out_path, src):
        with Image.open(src) as image:
            image = ImageOps.exif_transpose(image)
            if pil_format == "JPEG":
                image = flatten_to_rgb(image)
            image.save(out_path, format=pil_format)
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.{out_ext}"}


@app.post("/api/convert/image-to-pdf")
def convert_image_to_pdf(file: UploadFile = File(...)):
    src = save_upload(file, ".img")
    file_id, out_path = new_output("pdf")
    with conversion(out_path, src):
        with Image.open(src) as image:
            image = flatten_to_rgb(ImageOps.exif_transpose(image))
            image.save(out_path, "PDF")
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.pdf"}


MAX_RESIZE_DIMENSION = 8000


@app.post("/api/convert/image-resizer")
def resize_image(file: UploadFile = File(...), width: int = Form(...), height: int = Form(...)):
    if not (1 <= width <= MAX_RESIZE_DIMENSION and 1 <= height <= MAX_RESIZE_DIMENSION):
        raise HTTPException(status_code=400,
                            detail=f"Width and height must be between 1 and {MAX_RESIZE_DIMENSION} pixels.")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".png"
    src = save_upload(file, ".img")
    file_id, out_path = new_output(ext.lstrip("."))
    with conversion(out_path, src):
        with Image.open(src) as image:
            image = ImageOps.exif_transpose(image)
            if ext in (".jpg", ".jpeg"):
                image = flatten_to_rgb(image)
            image.resize((width, height), Image.Resampling.LANCZOS).save(out_path)
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}_resized{ext}"}


@app.post("/api/convert/compress-image")
def compress_image(file: UploadFile = File(...), quality: int = Form(...)):
    quality = max(1, min(100, quality))
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".jpg", ".jpeg", ".webp"):
        ext = ".jpg"
    src = save_upload(file, ".img")
    file_id, out_path = new_output(ext.lstrip("."))
    with conversion(out_path, src):
        with Image.open(src) as image:
            image = ImageOps.exif_transpose(image)
            if ext in (".jpg", ".jpeg"):
                image = flatten_to_rgb(image)
            save_format = "JPEG" if ext in (".jpg", ".jpeg") else "WEBP"
            image.save(out_path, format=save_format, quality=quality, optimize=True)
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}_compressed{ext}"}


@app.post("/api/convert/mp4-to-mp3")
def convert_mp4_to_mp3(file: UploadFile = File(...)):
    src = save_upload(file, ".mp4")
    file_id, out_path = new_output("mp3")
    with conversion(out_path, src, heavy=True):
        video = VideoFileClip(src)
        try:
            if video.audio is None:
                raise HTTPException(status_code=400, detail="No audio track found in the video file.")
            video.audio.write_audiofile(out_path, logger=None)
        finally:
            video.close()
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.mp3"}


@app.post("/api/convert/wav-to-mp3")
def convert_wav_to_mp3(file: UploadFile = File(...)):
    src = save_upload(file, ".wav")
    file_id, out_path = new_output("mp3")
    with conversion(out_path, src, heavy=True):
        audio = AudioFileClip(src)
        try:
            audio.write_audiofile(out_path, logger=None)
        finally:
            audio.close()
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.mp3"}


@app.post("/api/convert/avi-to-mp4")
def convert_avi_to_mp4(file: UploadFile = File(...)):
    src = save_upload(file, ".avi")
    file_id, out_path = new_output("mp4")
    with conversion(out_path, src, heavy=True):
        video = VideoFileClip(src)
        try:
            video.write_videofile(out_path, audio_codec="aac", logger=None)  # AAC: the MP4 standard (moviepy defaults to MP3)
        finally:
            video.close()
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.mp4"}


@app.post("/api/convert/mp3-to-mp4")
def convert_mp3_to_mp4(file: UploadFile = File(...)):
    src = save_upload(file, ".mp3")
    file_id, out_path = new_output("mp4")
    with conversion(out_path, src, heavy=True):
        audio = AudioFileClip(src)
        clip = None
        try:
            clip = ColorClip(size=(640, 480), color=(0, 0, 0), duration=audio.duration).with_audio(audio)
            clip.write_videofile(out_path, fps=1, audio_codec="aac", logger=None)
        finally:
            if clip is not None:
                clip.close()
            audio.close()
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.mp4"}


PDF_TO_JPG_DPI = 150
PDF_TO_JPG_MAX_PAGES = 50
PDF_TO_JPG_QUALITY = 85
PDF_TO_JPG_MAX_PIXELS = 25_000_000   # per page (~75 MB RGB) — oversized pages are rendered at a lower DPI
pdfium_lock = threading.Lock()   # PDFium is not thread-safe; sync endpoints run in a threadpool


@app.post("/api/convert/pdf-to-jpg")
def convert_pdf_to_jpg(file: UploadFile = File(...)):
    stem = safe_stem(file.filename)
    src = save_upload(file, ".pdf")
    file_id, out_path = None, None
    with conversion("", src, heavy=True), pdfium_lock:
        pdf = pdfium.PdfDocument(src)
        try:
            n = len(pdf)
            if n == 0:
                raise HTTPException(status_code=400, detail=GENERIC_FAILURE)
            if n > PDF_TO_JPG_MAX_PAGES:
                raise HTTPException(status_code=400, detail=(
                    f"This PDF has {n} pages. The free converter handles up to {PDF_TO_JPG_MAX_PAGES} "
                    "pages per file. Please split the PDF and try again."))
            scale = PDF_TO_JPG_DPI / 72
            if n == 1:
                file_id, out_path = new_output("jpg")
                try:
                    _render_pdf_page(pdf, 0, scale).save(out_path, "JPEG", quality=PDF_TO_JPG_QUALITY, optimize=True)
                except BaseException:
                    cleanup_file(out_path)
                    raise
                filename = f"{stem}.jpg"
            else:
                file_id, out_path = new_output("zip")
                try:
                    # One page in memory at a time keeps RAM flat on Render's 512 MB instance.
                    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_STORED) as zf:
                        for i in range(n):
                            buf = io.BytesIO()
                            _render_pdf_page(pdf, i, scale).save(buf, "JPEG", quality=PDF_TO_JPG_QUALITY,
                                                                 optimize=True)
                            zf.writestr(f"{stem}-page-{i + 1}.jpg", buf.getvalue())
                except BaseException:
                    cleanup_file(out_path)
                    raise
                filename = f"{stem}_jpg.zip"
        finally:
            pdf.close()
    return {"file_id": file_id, "filename": filename}


def _render_pdf_page(pdf, index: int, scale: float) -> Image.Image:
    page = pdf[index]
    try:
        w_pt, h_pt = page.get_size()
        pixels = max(1.0, w_pt * scale) * max(1.0, h_pt * scale)
        if pixels > PDF_TO_JPG_MAX_PIXELS:
            scale *= (PDF_TO_JPG_MAX_PIXELS / pixels) ** 0.5
        bitmap = page.render(scale=scale)
        try:
            return flatten_to_rgb(bitmap.to_pil())
        finally:
            bitmap.close()
    finally:
        page.close()


@app.post("/api/convert/heic-to-jpg")
def convert_heic_to_jpg(file: UploadFile = File(...)):
    src = save_upload(file, ".heic")
    file_id, out_path = new_output("jpg")
    with conversion(out_path, src, heavy=True):
        with Image.open(src) as image:
            # exif_transpose bakes the orientation into the pixels; EXIF is not copied to the JPG.
            image = flatten_to_rgb(ImageOps.exif_transpose(image))
            image.save(out_path, "JPEG", quality=92, optimize=True)
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.jpg"}


GIF_MAX_SECONDS = 15
GIF_FPS = 12
GIF_MAX_WIDTH = 480
GIF_MAX_HEIGHT = 480
GIF_TIMEOUT_SECONDS = 120


@app.post("/api/convert/mp4-to-gif")
def convert_mp4_to_gif(file: UploadFile = File(...)):
    if not FFMPEG_PATH:
        raise HTTPException(status_code=503, detail="Video conversion is temporarily unavailable on this server.")
    src = save_upload(file, ".mp4")
    file_id, out_path = new_output("gif")
    palette = out_path + ".palette.png"
    with conversion(out_path, src, palette, heavy=True):
        # Bounding box keeps memory flat for portrait/odd aspect ratios; two passes (palettegen,
        # then paletteuse) stream frames instead of buffering the whole clip in RAM.
        base = (f"fps={GIF_FPS},scale=w='min({GIF_MAX_WIDTH},iw)':h='min({GIF_MAX_HEIGHT},ih)'"
                ":force_original_aspect_ratio=decrease:flags=lanczos,scale=trunc(iw/2)*2:trunc(ih/2)*2")
        common = [FFMPEG_PATH, "-y", "-loglevel", "error", "-t", str(GIF_MAX_SECONDS), "-i", src]
        _run_ffmpeg(common + ["-vf", f"{base},palettegen=stats_mode=diff", "-frames:v", "1",
                              "-update", "1", palette])
        _run_ffmpeg(common + ["-i", palette, "-lavfi",
                              f"{base}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
                              "-loop", "0", "-f", "gif", out_path])
        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            raise RuntimeError("ffmpeg produced no GIF")
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.gif"}


GIF_TO_MP4_MAX_SECONDS = 30
GIF_TO_MP4_MAX_SIDE = 720


@app.post("/api/convert/gif-to-mp4")
def convert_gif_to_mp4(file: UploadFile = File(...)):
    if not FFMPEG_PATH:
        raise HTTPException(status_code=503, detail="Video conversion is temporarily unavailable on this server.")
    src = save_upload(file, ".gif")
    file_id, out_path = new_output("mp4")
    with conversion(out_path, src, heavy=True):
        # Fit inside 720x720 (never upscale), force even dimensions for yuv420p/H.264, and composite
        # GIF transparency onto white so it does not turn black. 2 threads keep RAM flat on 512 MB.
        vf = (f"scale=w='min({GIF_TO_MP4_MAX_SIDE},iw)':h='min({GIF_TO_MP4_MAX_SIDE},ih)'"
              ":force_original_aspect_ratio=decrease:flags=lanczos,"
              "pad=ceil(iw/2)*2:ceil(ih/2)*2:color=white,format=yuv420p")
        _run_ffmpeg([FFMPEG_PATH, "-y", "-loglevel", "error", "-t", str(GIF_TO_MP4_MAX_SECONDS),
                     "-i", src, "-filter_complex",
                     f"color=white:s=16x16[bg];[bg][0:v]scale2ref[bg2][fg];[bg2][fg]overlay=shortest=1,{vf}",
                     "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-threads", "2",
                     "-movflags", "+faststart", out_path])
        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            raise RuntimeError("ffmpeg produced no MP4")
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.mp4"}


QR_MAX_CHARS = 1000
QR_TARGET_PX = 1000


@app.post("/api/convert/qr-code-generator")
def generate_qr_code(text: str = Form(...)):
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Please enter a link or some text for your QR code.")
    if len(text) > QR_MAX_CHARS:
        raise HTTPException(status_code=400,
                            detail=f"Text is too long for a reliable QR code. Please keep it under {QR_MAX_CHARS} characters.")
    file_id, out_path = new_output("png")
    with conversion(out_path):
        qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_M, border=4, box_size=1)
        qr.add_data(text)
        qr.make(fit=True)
        modules = qr.modules_count + 2 * qr.border
        qr.box_size = max(4, QR_TARGET_PX // modules)
        qr.make_image(fill_color="black", back_color="white").get_image().convert("L").save(out_path, "PNG", optimize=True)
    return {"file_id": file_id, "filename": "qr-code.png"}


def _run_ffmpeg(cmd) -> None:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=GIF_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg timed out")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {proc.stderr[-300:].decode(errors='replace')}")


# --------------------------------------------------------------------------- #
# PDF Tools: merge / split / compress / rotate (pypdf, pure Python, thread-safe per request)
# --------------------------------------------------------------------------- #

PDF_TOOLS_MAX_PAGES = 200
MERGE_MAX_FILES = 10
SPLIT_MAX_OUTPUT_BYTES = 100 * 1024 * 1024
PDF_PASSWORD_MESSAGE = ("This PDF is password-protected. Please remove the password (open it and "
                        "re-save or print to PDF) and try again.")
COMPRESS_MAX_IMAGE_SIDE = 1600          # ~150 DPI on a Letter/A4 page
COMPRESS_JPEG_QUALITY = 70
COMPRESS_JPEG_MAX_BYTES_PER_PIXEL = 0.35  # JPEGs denser than this (e.g. quality 95-100 scans) get re-encoded
COMPRESS_MAX_SOURCE_PIXELS = 16_000_000  # never decode bigger images into RAM (512 MB instance)


def _open_pdf(path: str, page_budget: int = PDF_TOOLS_MAX_PAGES) -> PdfReader:
    reader = PdfReader(path, strict=False)
    if reader.is_encrypted:
        try:
            ok = reader.decrypt("")
        except Exception:
            ok = 0
        if not ok:
            raise HTTPException(status_code=400, detail=PDF_PASSWORD_MESSAGE)
    n = len(reader.pages)
    if n == 0:
        raise HTTPException(status_code=400, detail=GENERIC_FAILURE)
    if n > page_budget:
        raise HTTPException(status_code=400, detail=(
            f"This PDF has too many pages. The free PDF tools handle up to {PDF_TOOLS_MAX_PAGES} pages. "
            "Please split it into smaller files and try again."))
    return reader


def _write_pdf(writer: PdfWriter, path: str) -> None:
    with open(path, "wb") as fh:
        writer.write(fh)


def _parse_page_spec(spec: str, n: int) -> list:
    """'1-3, 5' -> [0, 1, 2, 4] (zero-based, in the order given). Raises 400 on anything invalid."""
    bad = HTTPException(status_code=400, detail=(
        f"Invalid page selection. Use page numbers between 1 and {n}, for example 1-3, 5."))
    spec = (spec or "").strip()
    if len(spec) > 200:
        raise bad
    out = []
    for part in spec.split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d{1,6})(?:\s*-\s*(\d{1,6}))?", part)
        if not m:
            raise bad
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        if not (1 <= a <= b <= n):
            raise bad
        out.extend(range(a - 1, b))
    if not out or len(out) > PDF_TOOLS_MAX_PAGES:
        raise bad
    return out


@app.post("/api/convert/merge-pdf")
def merge_pdf(files: list[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Please select at least 2 PDF files to merge.")
    if len(files) > MERGE_MAX_FILES:
        raise HTTPException(status_code=400, detail=f"You can merge up to {MERGE_MAX_FILES} PDF files at once.")
    srcs = []
    try:
        for f in files:
            srcs.append(save_upload(f, ".pdf"))
    except BaseException:
        for p in srcs:
            cleanup_file(p)
        raise
    file_id, out_path = new_output("pdf")
    with conversion(out_path, *srcs, heavy=True), pdf_apply_configuration(PDF_LIMITS):
        writer = PdfWriter()
        total = 0
        for p in srcs:
            reader = _open_pdf(p, PDF_TOOLS_MAX_PAGES - total)
            total += len(reader.pages)
            writer.append(reader)
        _write_pdf(writer, out_path)
    return {"file_id": file_id, "filename": "merged.pdf"}


@app.post("/api/convert/split-pdf")
def split_pdf(file: UploadFile = File(...), pages: str = Form("")):
    stem = safe_stem(file.filename)
    src = save_upload(file, ".pdf")
    if pages.strip():
        file_id, out_path = new_output("pdf")
        filename = f"{stem}_pages.pdf"
    else:
        file_id, out_path = new_output("zip")
        filename = f"{stem}_split.zip"
    with conversion(out_path, src, heavy=True), pdf_apply_configuration(PDF_LIMITS):
        reader = _open_pdf(src)
        n = len(reader.pages)
        if pages.strip():
            writer = PdfWriter()
            for i in _parse_page_spec(pages, n):
                writer.add_page(reader.pages[i])
            _write_pdf(writer, out_path)
        else:
            with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for i in range(n):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[i])
                    buf = io.BytesIO()
                    writer.write(buf)
                    zf.writestr(f"{stem}-page-{i + 1}.pdf", buf.getvalue())
                    # Each single-page PDF carries its own copy of shared fonts/images: bound the disk usage.
                    if os.path.getsize(out_path) > SPLIT_MAX_OUTPUT_BYTES:
                        raise HTTPException(status_code=400, detail=(
                            "This PDF is too large to split into single pages for free. Try extracting a "
                            "page range instead, for example 1-20."))
    return {"file_id": file_id, "filename": filename}


@app.post("/api/convert/rotate-pdf")
def rotate_pdf(file: UploadFile = File(...), angle: int = Form(...)):
    if angle not in (90, 180, 270):
        raise HTTPException(status_code=400, detail="Choose a rotation of 90, 180 or 270 degrees.")
    src = save_upload(file, ".pdf")
    file_id, out_path = new_output("pdf")
    with conversion(out_path, src, heavy=True), pdf_apply_configuration(PDF_LIMITS):
        writer = PdfWriter(clone_from=_open_pdf(src))
        for page in writer.pages:
            page.rotate(angle)
        _write_pdf(writer, out_path)
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}_rotated.pdf"}


def _downsample_pdf_images(writer: PdfWriter) -> None:
    """Re-encode large opaque raster images as JPEG at ~150 DPI. Skips masks/transparency and anything risky."""
    done = set()
    for page in writer.pages:
        try:
            xobjs = page["/Resources"].get_object().get("/XObject")
        except Exception:
            continue
        if not xobjs:
            continue
        xobjs = xobjs.get_object()
        for name in list(xobjs.keys()):
            try:
                xobj = xobjs[name].get_object()
                ref = xobjs[name].indirect_reference if hasattr(xobjs[name], "indirect_reference") else None
                key = (ref.idnum, ref.generation) if ref is not None else id(xobj)
                if key in done or xobj.get("/Subtype") != "/Image":
                    continue
                done.add(key)
                if "/SMask" in xobj or "/Mask" in xobj or xobj.get("/ImageMask"):
                    continue
                w, h = int(xobj.get("/Width", 0)), int(xobj.get("/Height", 0))
                if w * h <= 0 or w * h > COMPRESS_MAX_SOURCE_PIXELS:
                    continue
                if max(w, h) <= COMPRESS_MAX_IMAGE_SIDE and xobj.get("/Filter") == "/DCTDecode":
                    raw = getattr(xobj, "_data", b"") or b""
                    if len(raw) <= w * h * COMPRESS_JPEG_MAX_BYTES_PER_PIXEL:
                        continue  # already a reasonably sized, efficiently encoded JPEG
                image_file = page.images[name]
                img = image_file.image
                if img is None:
                    continue
                img = flatten_to_rgb(img) if img.mode not in ("L", "RGB") else img
                img.thumbnail((COMPRESS_MAX_IMAGE_SIDE, COMPRESS_MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
                image_file.replace(img, quality=COMPRESS_JPEG_QUALITY)
            except Exception:
                log.debug("compress-pdf: skipped image %s", name, exc_info=True)
                continue


@app.post("/api/convert/compress-pdf")
def compress_pdf(file: UploadFile = File(...)):
    src = save_upload(file, ".pdf")
    src_size = os.path.getsize(src)
    file_id, out_path = new_output("pdf")
    with conversion(out_path, src, heavy=True), pdf_apply_configuration(PDF_LIMITS):
        writer = PdfWriter(clone_from=_open_pdf(src))
        _downsample_pdf_images(writer)
        for page in writer.pages:
            try:
                page.compress_content_streams()
            except Exception:
                log.debug("compress-pdf: content stream not compressible", exc_info=True)
        writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        _write_pdf(writer, out_path)
        if os.path.getsize(out_path) >= src_size:
            shutil.copyfile(src, out_path)  # never hand back a bigger file
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}_compressed.pdf"}


@_page("/blog")
async def blog_index(request: Request):
    categories = []
    for cat_name, slugs in BLOG_CATEGORIES:
        articles = [BLOG_ARTICLES[s] for s in slugs if s in BLOG_ARTICLES]
        categories.append((cat_name, articles))
    return render(
        request, "blog_index.html", categories=categories,
        page_title="Blog — File Conversion Guides & Tutorials | PureFileConverter",
        page_description="Free guides on converting PDF, Word, Excel, images, audio and video. "
                         "Learn the best free methods for every file format with step-by-step tutorials.",
    )


@_page("/blog/{article_slug}")
async def blog_article(request: Request, article_slug: str):
    if article_slug in REMOVED_ARTICLE_REDIRECTS:  # pruned thin articles: one permanent hop to their tool
        return RedirectResponse(SITE_URL + REMOVED_ARTICLE_REDIRECTS[article_slug], status_code=301)
    if article_slug not in BLOG_ARTICLES:
        raise HTTPException(status_code=404, detail="Article not found")
    article = BLOG_ARTICLES[article_slug]
    # Related articles: same category, excluding current
    cat_name = article["category"]
    related = []
    for cn, slugs in BLOG_CATEGORIES:
        if cn == cat_name:
            for s in slugs:
                if s != article_slug and s in BLOG_ARTICLES:
                    a = BLOG_ARTICLES[s]
                    related.append({"slug": s, "title": a["title"], "description": a["description"],
                                   "category": a["category"]})
                    if len(related) >= 3:
                        break
            break
    return render(
        request, "blog_article.html", **article, related_articles=related[:3],
        jsonld_blocks=blog_article_jsonld(article),
        page_title=f"{article['title']} | PureFileConverter",
        page_description=article["description"],
    )


# --------------------------------------------------------------------------- #
# Tool pages (must stay LAST: catch-all slug route)
# --------------------------------------------------------------------------- #

@_page("/{tool_slug}")
async def tool_page(request: Request, tool_slug: str):
    if tool_slug not in TOOLS_CONFIG:
        raise HTTPException(status_code=404, detail="Page not found")
    tool = TOOLS_CONFIG[tool_slug]
    faqs = build_faqs(tool)
    # Related tools: same category, excluding current
    related = [t for t in TOOLS_CONFIG.values() if t["category"] == tool["category"] and t["slug"] != tool_slug][:3]
    if tool.get("seo_title"):
        page_title = f"{tool['seo_title']} | PureFileConverter"
    else:
        src_fmt, dst_fmt = tool["title"].split(" to ", 1)
        page_title = f"{tool['title']} Online Free – Convert {src_fmt} to {dst_fmt} | PureFileConverter"
    page_description = tool.get("meta") or (f"{tool['description']} Free online {tool['title']} converter - "
                                            f"no signup, files auto-deleted after 1 hour.")
    return render(
        request, "tool.html", tool=tool, faqs=faqs, related_tools=related,
        jsonld_blocks=tool_jsonld(tool, faqs),
        page_title=page_title,
        page_description=page_description,
    )
