import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.config import settings, BASE_DIR
from core.document_store import doc_store
from api.admin_routes import router as admin_router
from api.dynamic_routes import router as dynamic_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("doc_platform")

@asynccontextmanager
async def lifespan(app: FastAPI):
    docs = doc_store.list_all()
    logger.info("=" * 60)
    logger.info("🚀 Autonomous AI Document Extraction & API Generator Platform")
    logger.info(f"📁 Active Published Document APIs: {len(docs)}")
    for d in docs:
        logger.info(f"   • /api/v1/extract/{d.get('slug')} -> '{d.get('name')}'")
    
    if settings.api_key:
        logger.info("🔑 Gemini API Key: Configured")
    else:
        logger.warning("⚠️  Gemini API Key: NOT configured. Configure it via Admin UI at http://localhost:8000")
    logger.info("=" * 60)
    yield
    logger.info("Shutting down Document Extraction Platform.")

app = FastAPI(
    title="Autonomous AI Document Extraction & Dynamic API Platform",
    description="No-Code Document Intelligence Microservice - Automatically synthesizes schemas and provisions live REST APIs",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Mendix, Angular, React, Vue, and third-party callers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(admin_router)
app.include_router(dynamic_router)

# Mount Static UI
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serves the Admin Document Studio UI"""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Admin Studio UI is initializing. Please refresh in a moment."}

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Service liveness probe"""
    return {
        "status": "ONLINE",
        "service": "Autonomous Document Extraction Platform",
        "active_apis": len(doc_store.list_all()),
        "has_api_key": bool(settings.api_key.strip())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
