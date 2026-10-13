"""PureFileConverter - FastAPI backend.

Configuration (all optional, via environment variables):
    MAX_UPLOAD_MB            Max upload size per file in MB (default 10)
    SITE_URL                 Public base URL used for canonical/sitemap (default https://cleanfileconverter.com)
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
import uuid
from collections import deque
from contextlib import asynccontextmanager, contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
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
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "contact@purefileconverter.com")
LEGAL_UPDATED = "October 6, 2026"

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
templates.env.globals.update(
    site_url=SITE_URL,
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
}

for _slug, _tool in TOOLS_CONFIG.items():
    _tool["slug"] = _slug
    _tool["badge"] = COLOR_CLASSES[_tool["color"]]

TOOLS_BY_CATEGORY = [
    {**cat, "tools": [t for t in TOOLS_CONFIG.values() if t["category"] == cat["name"]]}
    for cat in CATEGORIES
]
templates.env.globals["tools_by_category"] = TOOLS_BY_CATEGORY

LEGAL_PAGES = ["privacy", "terms", "contact", "about"]

# --------------------------------------------------------------------------- #
# Blog
# --------------------------------------------------------------------------- #

from blog_data import BLOG_ARTICLES, BLOG_CATEGORIES

def blog_article_jsonld(article: dict) -> list:
    url = f"{SITE_URL}/blog/{article['slug']}"
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["title"],
        "description": article["description"],
        "url": url,
        "datePublished": "2026-10-11",
        "dateModified": "2026-10-11",
        "author": {
            "@type": "Organization",
            "name": "PureFileConverter",
            "url": SITE_URL,
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
        "description": "Free online file converter for documents, images, audio and video. No signup, no watermarks.",
        "knowsAbout": [
            "File conversion", "PDF conversion", "Document conversion",
            "Image processing", "Audio extraction", "Video transcoding",
            "Online converter tools",
        ],
        "sameAs": [
            "https://github.com/omareg03/cleanfileconverter",
        ],
    }
    return render(
        request, "index.html",
        page_title="Free Online File Converter - PDF, Word, Image, Audio & Video | PureFileConverter",
        page_description="Free online file converter: PDF to Word, Word to PDF, CSV to Excel, image converter, "
                         "MP4 to MP3 and more. No signup. Files are automatically deleted after 1 hour.",
        jsonld_blocks=[jsonld_dumps(website), jsonld_dumps(org)],
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
        f"12 dedicated conversion tools and 100 in-depth conversion guides.\n\n"
        f"## Document Tools\n"
        f"- [PDF to Word]({SITE_URL}/pdf-to-word): Convert PDF files into editable DOCX documents.\n"
        f"- [Word to PDF]({SITE_URL}/word-to-pdf): Convert DOC and DOCX files to PDF.\n"
        f"- [CSV to Excel]({SITE_URL}/csv-to-excel): Convert CSV files to styled XLSX workbooks.\n"
        f"- [Excel to PDF]({SITE_URL}/excel-to-pdf): Convert Excel spreadsheets to print-ready PDF.\n\n"
        f"## Image Tools\n"
        f"- [Image Converter]({SITE_URL}/image-converter): Convert between JPG, PNG and WebP.\n"
        f"- [Image to PDF]({SITE_URL}/image-to-pdf): Convert JPG, PNG, WebP images to PDF.\n"
        f"- [Image Resizer]({SITE_URL}/image-resizer): Resize images to exact dimensions.\n"
        f"- [Compress Image]({SITE_URL}/compress-image): Compress JPG and WebP images.\n\n"
        f"## Media Tools\n"
        f"- [MP4 to MP3]({SITE_URL}/mp4-to-mp3): Extract audio from MP4 video.\n"
        f"- [WAV to MP3]({SITE_URL}/wav-to-mp3): Convert WAV audio to MP3.\n"
        f"- [AVI to MP4]({SITE_URL}/avi-to-mp4): Convert AVI video to MP4 (H.264).\n"
        f"- [MP3 to MP4]({SITE_URL}/mp3-to-mp4): Create a static video from an MP3 audio file.\n\n"
        f"## Blog & Guides\n"
        f"- [Blog]({SITE_URL}/blog): File conversion guides and tutorials.\n"
        f"- [How to Convert PDF to Word]({SITE_URL}/blog/how-to-convert-pdf-to-word): Step-by-step guide.\n"
        f"- [How to Convert Word to PDF]({SITE_URL}/blog/how-to-convert-word-to-pdf): Free online guide.\n"
        f"- [How to Convert CSV to Excel]({SITE_URL}/blog/how-to-convert-csv-to-excel): Data conversion guide.\n"
        f"- [How to Resize Images Online]({SITE_URL}/blog/how-to-resize-images-online): Image resizing guide.\n"
        f"- [How to Compress JPG Images]({SITE_URL}/blog/how-to-compress-jpg-images): Compression guide.\n"
        f"- [How to Convert PNG to JPG]({SITE_URL}/blog/how-to-convert-png-to-jpg): Format conversion guide.\n"
        f"- [How to Extract Audio from MP4]({SITE_URL}/blog/how-to-extract-audio-from-mp4): Audio extraction guide.\n"
        f"- [How to Convert WAV to MP3]({SITE_URL}/blog/how-to-convert-wav-to-mp3): Audio compression guide.\n"
        f"- [How to Convert AVI to MP4]({SITE_URL}/blog/how-to-convert-avi-to-mp4): Video conversion guide.\n"
        f"- [How to Convert MP3 to MP4]({SITE_URL}/blog/how-to-convert-mp3-to-mp4): Audio to video guide.\n"
        f"- [Best Free File Converters 2026]({SITE_URL}/blog/best-free-file-converters-2026): Ranked comparison.\n"
        f"- [iLovePDF vs Smallpdf vs PureFileConverter]({SITE_URL}/blog/ilovepdf-vs-smallpdf-vs-purefileconverter): Feature comparison.\n"
        f"- [Why PDF to Word Loses Formatting]({SITE_URL}/blog/why-pdf-to-word-loses-formatting): Troubleshooting guide.\n"
        f"- [What Is WebP]({SITE_URL}/blog/what-is-webp-why-use-it): Image format guide.\n"
        f"- [Is It Safe to Convert Files Online]({SITE_URL}/blog/is-it-safe-to-convert-files-online): Privacy guide.\n\n"
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
            video.write_videofile(out_path, logger=None)
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
            clip.write_videofile(out_path, fps=1, logger=None)
        finally:
            if clip is not None:
                clip.close()
            audio.close()
    return {"file_id": file_id, "filename": f"{safe_stem(file.filename)}.mp4"}


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
    return render(
        request, "tool.html", tool=tool, faqs=faqs, related_tools=related,
        jsonld_blocks=tool_jsonld(tool, faqs),
        page_title=f"{tool['title']} Online Free – Convert {tool['title'].split(' to ')[0]} to {tool['title'].split(' to ')[-1] if ' to ' in tool['title'] else 'Any Format'} | PureFileConverter",
        page_description=f"{tool['description']} Free online {tool['title']} converter - no signup, "
                         f"files auto-deleted after 1 hour.",
    )
