import os

server_code = """import os
import uuid
import tempfile
import asyncio
import shutil
import threading
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Request, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
from pdf2docx import Converter
from docx2pdf import convert as docx2pdf_convert
from PIL import Image
from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip

app = FastAPI(title="Free File Converter API")

TEMP_DIR = os.path.join(tempfile.gettempdir(), "free_file_converter")
os.makedirs(TEMP_DIR, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=BASE_DIR)

def cleanup_file(path: str):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            print(f"Error cleaning up file {path}: {e}")

async def delayed_cleanup(path: str, delay: int = 3600):
    await asyncio.sleep(delay)
    cleanup_file(path)

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

@app.get("/download-page", response_class=HTMLResponse)
async def download_page(request: Request, file_id: str, filename: str):
    return templates.TemplateResponse(request=request, name="download.html", context={"request": request, "file_id": file_id, "filename": filename})

@app.get("/api/download/{file_id}")
async def download_file(file_id: str, filename: str, background_tasks: BackgroundTasks):
    file_path = os.path.join(TEMP_DIR, file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found or already downloaded.")
    
    background_tasks.add_task(cleanup_file, file_path)
    return FileResponse(path=file_path, filename=filename)

@app.post("/api/convert/csv-to-excel")
def convert_csv_to_excel(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4()) + ".xlsx"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    try:
        df = pd.read_csv(file.file)
        df.to_excel(out_path, index=False)
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}.xlsx"}

@app.post("/api/convert/pdf-to-word")
def convert_pdf_to_word(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4()) + ".docx"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    temp_pdf = os.path.join(TEMP_DIR, str(uuid.uuid4()) + ".pdf")
    with open(temp_pdf, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        cv = Converter(temp_pdf)
        cv.convert(out_path, start=0, end=None)
        cv.close()
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    finally:
        cleanup_file(temp_pdf)
        
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}.docx"}

word_lock = threading.Lock()

@app.post("/api/convert/word-to-pdf")
def convert_word_to_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4()) + ".pdf"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".doc", ".docx"]:
        ext = ".docx"

    temp_docx = os.path.join(TEMP_DIR, str(uuid.uuid4()) + ext)
    with open(temp_docx, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        with word_lock:
            import pythoncom
            pythoncom.CoInitialize()
            docx2pdf_convert(temp_docx, out_path)
    except Exception as e:
        cleanup_file(out_path)
        err_str = str(e).lower()
        if "com" in err_str or "word" in err_str or "dispatch" in err_str:
            msg = "Conversion failed: Microsoft Word is required on the server for this feature."
        else:
            msg = f"Conversion failed: {str(e)}"
        raise HTTPException(status_code=400, detail=msg)
    finally:
        cleanup_file(temp_docx)
        
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}.pdf"}

excel_lock = threading.Lock()

@app.post("/api/convert/excel-to-pdf")
def convert_excel_to_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4()) + ".pdf"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".xls", ".xlsx", ".csv"]:
        ext = ".xlsx"

    temp_excel = os.path.join(TEMP_DIR, str(uuid.uuid4()) + ext)
    with open(temp_excel, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        with excel_lock:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            wb = excel.Workbooks.Open(temp_excel)
            wb.ExportAsFixedFormat(0, out_path)
            wb.Close(False)
            excel.Quit()
    except Exception as e:
        cleanup_file(out_path)
        err_str = str(e).lower()
        if "com" in err_str or "excel" in err_str or "dispatch" in err_str:
            msg = "Conversion failed: Microsoft Excel is required on the server for this feature."
        else:
            msg = f"Conversion failed: {str(e)}"
        raise HTTPException(status_code=400, detail=msg)
    finally:
        cleanup_file(temp_excel)
        
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}.pdf"}

@app.post("/api/convert/image")
def convert_image(background_tasks: BackgroundTasks, file: UploadFile = File(...), format: str = Form(...)):
    ext = format.lower()
    if ext == 'jpg': 
        ext = 'jpeg'
    
    file_id = str(uuid.uuid4()) + f".{ext}"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    try:
        image = Image.open(file.file)
        if image.mode in ("RGBA", "P") and ext == "jpeg":
            image = image.convert("RGB")
        image.save(out_path, format=ext.upper())
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    output_ext = "jpg" if ext == "jpeg" else ext
    return {"file_id": file_id, "filename": f"{original_name}.{output_ext}"}

@app.post("/api/convert/image-to-pdf")
def convert_image_to_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4()) + ".pdf"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    try:
        image = Image.open(file.file)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(out_path, "PDF")
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}.pdf"}

@app.post("/api/convert/image-resizer")
def resize_image(background_tasks: BackgroundTasks, file: UploadFile = File(...), width: int = Form(...), height: int = Form(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        ext = ".png"
    file_id = str(uuid.uuid4()) + ext
    out_path = os.path.join(TEMP_DIR, file_id)
    
    try:
        image = Image.open(file.file)
        resized_image = image.resize((width, height), Image.Resampling.LANCZOS)
        resized_image.save(out_path)
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}_resized{ext}"}

@app.post("/api/convert/compress-image")
def compress_image(background_tasks: BackgroundTasks, file: UploadFile = File(...), quality: int = Form(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".webp"]:
        ext = ".jpg"
    file_id = str(uuid.uuid4()) + ext
    out_path = os.path.join(TEMP_DIR, file_id)
    
    try:
        image = Image.open(file.file)
        if image.mode in ("RGBA", "P") and ext in [".jpg", ".jpeg"]:
            image = image.convert("RGB")
        save_format = "JPEG" if ext in [".jpg", ".jpeg"] else "WEBP"
        image.save(out_path, format=save_format, quality=quality, optimize=True)
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}_compressed{ext}"}

@app.post("/api/convert/mp4-to-mp3")
def convert_mp4_to_mp3(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4()) + ".mp3"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    temp_mp4 = os.path.join(TEMP_DIR, str(uuid.uuid4()) + ".mp4")
    with open(temp_mp4, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        video = VideoFileClip(temp_mp4)
        if video.audio is None:
            video.close()
            raise ValueError("No audio track found in the video file.")
        video.audio.write_audiofile(out_path, logger=None)
        video.close()
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    finally:
        cleanup_file(temp_mp4)
        
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}.mp3"}

@app.post("/api/convert/wav-to-mp3")
def convert_wav_to_mp3(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4()) + ".mp3"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    temp_wav = os.path.join(TEMP_DIR, str(uuid.uuid4()) + ".wav")
    with open(temp_wav, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        audio = AudioFileClip(temp_wav)
        audio.write_audiofile(out_path, logger=None)
        audio.close()
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    finally:
        cleanup_file(temp_wav)
        
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}.mp3"}

@app.post("/api/convert/avi-to-mp4")
def convert_avi_to_mp4(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4()) + ".mp4"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    temp_avi = os.path.join(TEMP_DIR, str(uuid.uuid4()) + ".avi")
    with open(temp_avi, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        video = VideoFileClip(temp_avi)
        video.write_videofile(out_path, logger=None)
        video.close()
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    finally:
        cleanup_file(temp_avi)
        
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}.mp4"}

@app.post("/api/convert/mp3-to-mp4")
def convert_mp3_to_mp4(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4()) + ".mp4"
    out_path = os.path.join(TEMP_DIR, file_id)
    
    temp_mp3 = os.path.join(TEMP_DIR, str(uuid.uuid4()) + ".mp3")
    with open(temp_mp3, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        audio = AudioFileClip(temp_mp3)
        clip = ColorClip(size=(640, 480), color=(0, 0, 0), duration=audio.duration)
        clip = clip.set_audio(audio)
        clip.write_videofile(out_path, fps=1, logger=None)
        clip.close()
        audio.close()
    except Exception as e:
        cleanup_file(out_path)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")
    finally:
        cleanup_file(temp_mp3)
        
    background_tasks.add_task(delayed_cleanup, out_path, 3600)
    original_name = os.path.splitext(file.filename)[0]
    return {"file_id": file_id, "filename": f"{original_name}.mp4"}

TOOLS_CONFIG = {
    "pdf-to-word": {
        "title": "PDF to Word",
        "accept": ".pdf",
        "description": "Easily convert your PDF files into easy to edit DOCX documents.",
        "endpoint": "/api/convert/pdf-to-word",
        "has_format_selector": False,
        "icon": "fa-file-pdf",
        "color": "red"
    },
    "word-to-pdf": {
        "title": "Word to PDF",
        "accept": ".doc,.docx",
        "description": "Make DOC and DOCX files easy to read by converting them to PDF.",
        "endpoint": "/api/convert/word-to-pdf",
        "has_format_selector": False,
        "icon": "fa-file-word",
        "color": "blue"
    },
    "csv-to-excel": {
        "title": "CSV to Excel",
        "accept": ".csv",
        "description": "Convert CSV files to XLSX easily and accurately.",
        "endpoint": "/api/convert/csv-to-excel",
        "has_format_selector": False,
        "icon": "fa-file-csv",
        "color": "green"
    },
    "excel-to-pdf": {
        "title": "Excel to PDF",
        "accept": ".xls,.xlsx,.csv",
        "description": "Convert Excel spreadsheets to PDF format.",
        "endpoint": "/api/convert/excel-to-pdf",
        "has_format_selector": False,
        "icon": "fa-file-excel",
        "color": "emerald"
    },
    "image-converter": {
        "title": "Image Converter",
        "accept": "image/png, image/jpeg, image/webp",
        "description": "Convert JPG, PNG, and WebP images to your desired format.",
        "endpoint": "/api/convert/image",
        "has_format_selector": True,
        "icon": "fa-image",
        "color": "yellow"
    },
    "image-to-pdf": {
        "title": "Image to PDF",
        "accept": "image/png, image/jpeg, image/webp",
        "description": "Convert images into PDF documents.",
        "endpoint": "/api/convert/image-to-pdf",
        "has_format_selector": False,
        "icon": "fa-file-image",
        "color": "orange"
    },
    "image-resizer": {
        "title": "Image Resizer",
        "accept": "image/png, image/jpeg, image/webp",
        "description": "Resize your images to specific dimensions.",
        "endpoint": "/api/convert/image-resizer",
        "has_format_selector": False,
        "has_resize_inputs": True,
        "icon": "fa-down-left-and-up-right-to-center",
        "color": "teal"
    },
    "compress-image": {
        "title": "Compress Image",
        "accept": "image/jpeg, image/webp",
        "description": "Compress images to reduce file size.",
        "endpoint": "/api/convert/compress-image",
        "has_format_selector": False,
        "has_quality_input": True,
        "icon": "fa-compress",
        "color": "cyan"
    },
    "mp4-to-mp3": {
        "title": "MP4 to MP3",
        "accept": ".mp4",
        "description": "Extract audio from MP4 video files and save as MP3.",
        "endpoint": "/api/convert/mp4-to-mp3",
        "has_format_selector": False,
        "icon": "fa-file-audio",
        "color": "purple"
    },
    "wav-to-mp3": {
        "title": "WAV to MP3",
        "accept": ".wav",
        "description": "Convert WAV audio files to MP3 format.",
        "endpoint": "/api/convert/wav-to-mp3",
        "has_format_selector": False,
        "icon": "fa-music",
        "color": "indigo"
    },
    "avi-to-mp4": {
        "title": "AVI to MP4",
        "accept": ".avi",
        "description": "Convert AVI video files to MP4 format.",
        "endpoint": "/api/convert/avi-to-mp4",
        "has_format_selector": False,
        "icon": "fa-file-video",
        "color": "fuchsia"
    },
    "mp3-to-mp4": {
        "title": "MP3 to MP4",
        "accept": ".mp3",
        "description": "Create a static video from an MP3 audio file.",
        "endpoint": "/api/convert/mp3-to-mp4",
        "has_format_selector": False,
        "icon": "fa-film",
        "color": "pink"
    }
}

@app.get("/{tool_slug}", response_class=HTMLResponse)
async def tool_page(request: Request, tool_slug: str):
    if tool_slug not in TOOLS_CONFIG:
        raise HTTPException(status_code=404, detail="Page not found")
    tool = TOOLS_CONFIG[tool_slug]
    return templates.TemplateResponse(request=request, name="tool.html", context={"request": request, "tool": tool})
"""

with open("C:/Users/oegar/OneDrive/Documents/Free_File_Converter/server.py", "w", encoding="utf-8") as f:
    f.write(server_code)
