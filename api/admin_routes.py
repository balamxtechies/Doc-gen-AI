import time
import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from pydantic import BaseModel

from core.config import settings
from core.pdf_processor import process_document_to_images
from core.code_synthesizer import synthesize_document_code
from core.schema_engine import slugify
from core.document_store import doc_store
from core.llm_client import gemini_client
from core.service_generator import generate_microservice_package
from core.service_manager import service_manager

router = APIRouter(prefix="/api/v1/admin", tags=["Admin Studio"])
logger = logging.getLogger(__name__)

class PublishRequest(BaseModel):
    name: str
    slug: str
    description: Optional[str] = ""
    prompt: str
    fields: List[dict]
    json_schema: dict
    runtime_system_prompt: Optional[str] = ""
    python_code: str
    sample_output: Optional[dict] = None

class SettingsRequest(BaseModel):
    api_key: str
    default_model: Optional[str] = "gemini-flash-latest"

@router.get("/settings")
async def get_settings():
    """Returns current configuration with masked API key for security"""
    has_key = bool(settings.api_key.strip())
    masked = ""
    if has_key:
        k = settings.api_key.strip()
        masked = f"{k[:4]}...{k[-4:]}" if len(k) > 8 else "****"

    return {
        "has_api_key": has_key,
        "masked_api_key": masked,
        "default_model": settings.default_model
    }

@router.post("/settings")
async def update_settings(req: SettingsRequest):
    """Updates and verifies Gemini API Key and default model"""
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API Key cannot be empty.")

    valid, message = await gemini_client.test_connection(key, req.default_model or "gemini-flash-latest")
    if not valid:
        raise HTTPException(status_code=400, detail=f"API Key validation failed: {message}")

    settings.save_settings(key, req.default_model or "gemini-flash-latest")
    return {
        "success": True,
        "message": f"Settings saved and {settings.default_model} successfully verified!",
        "model": settings.default_model
    }

@router.post("/analyze")
async def analyze_sample_document(
    request: Request,
    name: str = Form(...),
    prompt: str = Form(...),
    model: Optional[str] = Form(None),
    files: List[UploadFile] = File(...)
):
    """
    Step 1: Admin uploads sample document(s) and prompt.
    Gemini is called ONLY ONCE here to generate pure, standalone Python extraction code!
    """
    t_start = time.time()

    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="Please upload at least one sample document (PDF or image).")

    all_images = []
    for f in files:
        file_bytes = await f.read()
        if not file_bytes:
            continue
        try:
            pages = process_document_to_images(file_bytes)
            all_images.extend(pages)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading file {f.filename}: {str(e)}")

    if not all_images:
        raise HTTPException(status_code=400, detail="Could not extract any pages/images from uploaded files.")

    try:
        # Gemini acts as Autonomous Code Synthesizer (One-Time Execution)
        analysis = await synthesize_document_code(
            doc_name=name,
            user_prompt=prompt,
            sample_images=all_images,
            model=model or settings.default_model or "gemini-flash-latest"
        )
        elapsed_ms = int((time.time() - t_start) * 1000)
        analysis["processing_time_ms"] = elapsed_ms
        analysis["total_pages_analyzed"] = len(all_images)
        return analysis
    except Exception as e:
        logger.error(f"Autonomous Code Synthesis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")

@router.post("/publish")
async def publish_document_api(req: PublishRequest, request: Request):
    """
    Step 2: Scaffolds standalone project in generated_services/{slug}/ and hosts it locally in parallel!
    The new service has ZERO AI calls.
    """
    safe_slug = slugify(req.slug or req.name)
    doc_id = f"doc_{safe_slug}"

    # 1. Allocate an available port for the new standalone microservice (e.g. 8001, 8002)
    assigned_port = service_manager.find_free_port()

    # 2. Write standalone microservice code to generated_services/{safe_slug}/
    service_dir = generate_microservice_package(
        slug=safe_slug,
        display_name=req.name,
        python_code=req.python_code,
        port=assigned_port,
        json_schema=req.json_schema
    )

    # 3. Launch the standalone microservice as a parallel background process
    service_info = service_manager.start_service(
        slug=safe_slug,
        name=req.name,
        port=assigned_port,
        service_dir=service_dir
    )

    host_url = str(request.base_url).rstrip("/")
    endpoint_url = f"{host_url}/api/v1/extract/{safe_slug}"
    standalone_url = f"http://localhost:{assigned_port}/extract"

    doc_data = {
        "id": doc_id,
        "slug": safe_slug,
        "name": req.name,
        "description": req.description or f"Autonomous Zero-AI Extraction Service for {req.name}",
        "prompt": req.prompt,
        "fields": req.fields,
        "json_schema": req.json_schema,
        "python_code": req.python_code,
        "sample_output": req.sample_output,
        "endpoint_url": endpoint_url,
        "standalone_url": standalone_url,
        "port": assigned_port,
        "service_dir": str(service_dir),
        "mode": "100% Local / Zero-AI"
    }

    saved = doc_store.save(doc_data)

    return {
        "success": True,
        "message": f"Zero-AI Microservice for '{req.name}' generated and hosted on port {assigned_port}!",
        "document": saved,
        "standalone_url": standalone_url,
        "endpoint_url": endpoint_url,
        "port": assigned_port,
        "service_dir": str(service_dir),
        "curl_example": f"""curl -X POST "{standalone_url}" \\
  -F "file=@sample_document.pdf" """
    }

@router.get("/documents")
async def list_documents(request: Request):
    """Lists all published document APIs with live URLs, schemas, and stats"""
    host_url = str(request.base_url).rstrip("/")
    docs = doc_store.list_all()
    for d in docs:
        d["endpoint_url"] = f"{host_url}/api/v1/extract/{d.get('slug')}"
    return docs

@router.get("/documents/{slug}")
async def get_document(slug: str, request: Request):
    """Retrieves full configuration of a specific published document API"""
    doc = doc_store.get_by_slug(slug)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document API '{slug}' not found.")
    host_url = str(request.base_url).rstrip("/")
    doc["endpoint_url"] = f"{host_url}/api/v1/extract/{doc.get('slug')}"
    return doc

@router.delete("/documents/{slug}")
async def delete_document(slug: str):
    """Deletes/deactivates a published document API"""
    success = doc_store.delete(slug)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document API '{slug}' not found.")
    return {"success": True, "message": f"Document API '{slug}' removed successfully."}
