import os
import shutil
from pathlib import Path
from typing import Dict, Any
from .config import BASE_DIR

SERVICES_DIR = BASE_DIR / "generated_services"
SERVICES_DIR.mkdir(exist_ok=True)

MICROSERVICE_MAIN_TEMPLATE = '''"""
Standalone Document Extraction Microservice for: {display_name}
Generated autonomously by DocuGen AI Studio.
100% OFFLINE, ZERO-AI DEPENDENCY: Uses local RapidOCR and deterministic Python logic.
"""
import time
import io
import cv2
import numpy as np
from PIL import Image
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rapidocr_onnxruntime import RapidOCR

from extractor import extract_document

app = FastAPI(
    title="{display_name} Extraction Microservice",
    description="Standalone Zero-AI Document Extractor - Autonomously Generated",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize local OCR engine (zero external API calls)
ocr_engine = RapidOCR(det_limit_side_len=720, det_limit_type="max", rec_batch_num=16)

def run_local_ocr_on_bytes(image_bytes: bytes):
    # Handle PDF if uploaded
    if image_bytes.startswith(b"%PDF"):
        import pypdfium2
        pdf = pypdfium2.PdfDocument(image_bytes)
        page = pdf[0]
        pil_img = page.render(scale=1.5).to_pil()
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    else:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode document image.")

    raw_results, _ = ocr_engine(img)
    if not raw_results:
        return [], ""

    items = []
    for box, text, conf in raw_results:
        clean_text = str(text).strip()
        if not clean_text:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append({{
            "text": clean_text,
            "confidence": float(conf),
            "cx": float(sum(xs) / 4.0),
            "cy": float(sum(ys) / 4.0),
            "min_x": float(min(xs)),
            "max_x": float(max(xs)),
            "min_y": float(min(ys)),
            "max_y": float(max(ys))
        }})

    items.sort(key=lambda x: x["cy"])
    full_text = "\\n".join(it["text"] for it in items)
    return items, full_text

@app.post("/extract")
async def extract_api(file: UploadFile = File(...)):
    """
    Zero-AI extraction endpoint. Runs 100% locally on CPU without calling Gemini or OpenAI.
    """
    t0 = time.time()
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    try:
        items, full_text = run_local_ocr_on_bytes(contents)
        # Call the generated Python extractor
        data = extract_document(items, full_text)
        elapsed_ms = int((time.time() - t0) * 1000)

        return {{
            "success": True,
            "status": "SUCCESS",
            "service": "{slug}",
            "processing_time_ms": elapsed_ms,
            "data": data,
            "mode": "100% Local / Zero-AI"
        }}
    except Exception as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        return {{
            "success": False,
            "status": "ERROR",
            "service": "{slug}",
            "processing_time_ms": elapsed_ms,
            "message": str(e)
        }}

@app.get("/health")
def health():
    return {{"status": "ONLINE", "service": "{slug}", "mode": "100% Local / Zero-AI"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port={port}, reload=False)
'''

RUN_BAT_TEMPLATE = """@echo off
title {display_name} Microservice (Port {port})
echo Starting Standalone Document Extraction Service for {display_name}...
echo Running locally on port {port} with ZERO AI API calls.
cd /d "%~dp0"
..\\..\\venv\\Scripts\\python.exe -m uvicorn main:app --host 0.0.0.0 --port {port}
pause
"""

def generate_microservice_package(
    slug: str,
    display_name: str,
    python_code: str,
    port: int,
    json_schema: Dict[str, Any]
) -> Path:
    """
    Scaffolds and writes the complete standalone project into generated_services/{slug}/
    """
    service_dir = SERVICES_DIR / slug
    service_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write the pure Python extractor
    extractor_file = service_dir / "extractor.py"
    with open(extractor_file, "w", encoding="utf-8") as f:
        f.write(python_code)

    # 2. Write the standalone FastAPI main.py
    main_file = service_dir / "main.py"
    main_code = MICROSERVICE_MAIN_TEMPLATE.format(
        display_name=display_name,
        slug=slug,
        port=port
    )
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(main_code)

    # 3. Write run.bat
    bat_file = service_dir / "run.bat"
    with open(bat_file, "w", encoding="utf-8") as f:
        f.write(RUN_BAT_TEMPLATE.format(
            display_name=display_name,
            port=port
        ))

    return service_dir
