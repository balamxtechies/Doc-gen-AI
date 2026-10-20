import time
import base64
import json
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Request, HTTPException

from core.document_store import doc_store
from core.service_manager import service_manager

router = APIRouter(prefix="/api/v1", tags=["Dynamic Extraction APIs"])
logger = logging.getLogger(__name__)

@router.post("/extract/{document_slug}")
async def dynamic_extract(
    document_slug: str,
    request: Request,
    file: Optional[UploadFile] = File(None)
):
    """
    Universal Dynamic Extraction Endpoint.
    100% OFFLINE, ZERO-AI DEPENDENCY:
    Executes ONLY the generated local Python code on the local CPU without calling Gemini!
    """
    t_start = time.time()
    slug = document_slug.strip().lower()

    # 1. Fetch document definition from persistent store
    doc_config = doc_store.get_by_slug(slug)
    if not doc_config:
        available_slugs = [d.get("slug") for d in doc_store.list_all()]
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"Document API endpoint '{slug}' does not exist.",
                "message": "Please configure and publish this document type in the Admin Studio first.",
                "available_endpoints": [f"/api/v1/extract/{s}" for s in available_slugs]
            }
        )

    # 2. Extract binary contents from any request format
    contents = None

    # A. Check multipart file
    if file is not None:
        contents = await file.read()

    # B. If not in 'file', scan all form parts
    if not contents or len(contents) == 0:
        try:
            form = await request.form()
            for key, val in form.items():
                if hasattr(val, "read"):
                    data = await val.read()
                    if data and len(data) > 0:
                        contents = data
                        break
        except Exception:
            pass

    # C. Check JSON base64 body or raw binary stream
    if not contents or len(contents) == 0:
        try:
            body = await request.body()
            if body and len(body) > 0:
                if body.startswith(b"{"):
                    data = json.loads(body)
                    b64_str = (
                        data.get("image_base64")
                        or data.get("document_base64")
                        or data.get("file_base64")
                        or data.get("file")
                        or ""
                    )
                    if b64_str:
                        if "," in b64_str:
                            b64_str = b64_str.split(",", 1)[1]
                        contents = base64.b64decode(b64_str)
                else:
                    contents = body
        except Exception as e:
            logger.debug(f"Error reading body as JSON base64: {e}")

    if not contents or len(contents) == 0:
        raise HTTPException(
            status_code=400,
            detail="No document binary data was received. Please provide a file via multipart form or base64 JSON."
        )

    # 3. Execute extraction using the autonomously generated Python code (ZERO-AI CALLS!)
    try:
        extracted_data = service_manager.execute_local_extraction(slug, contents)
        elapsed_ms = int((time.time() - t_start) * 1000)

        # Update metrics
        doc_store.increment_call_count(slug)

        return {
            "success": True,
            "status": "SUCCESS",
            "document_type": slug,
            "document_name": doc_config.get("name"),
            "processing_time_ms": elapsed_ms,
            "mode": "100% Local Generated Python / Zero-AI Call",
            "data": extracted_data
        }

    except Exception as e:
        elapsed_ms = int((time.time() - t_start) * 1000)
        logger.error(f"Local extraction error on '{slug}': {e}", exc_info=True)
        return {
            "success": False,
            "status": "ERROR",
            "document_type": slug,
            "processing_time_ms": elapsed_ms,
            "mode": "100% Local Generated Python / Zero-AI Call",
            "message": f"Local extraction failed: {str(e)}"
        }
