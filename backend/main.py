"""
AI Shorts & Video Factory — FastAPI Backend
Production-ready cloud video generation pipeline
"""

import os
import uuid
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from routers import script, assets, video
from utils.config import settings

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    Path("static/previews").mkdir(parents=True, exist_ok=True)
    logger.info("✅ AI Shorts Factory backend started — directories ready")
    yield
    logger.info("🛑 Backend shutting down")


app = FastAPI(
    title="AI Shorts & Video Factory API",
    description="Cloud-native AI video generation pipeline — free-tier, no GPU required.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving (generated thumbnails & previews)
os.makedirs("static/previews", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(script.router, prefix="/api/script", tags=["Script Generation"])
app.include_router(assets.router, prefix="/api/assets", tags=["Asset Generation"])
app.include_router(video.router, prefix="/api/video", tags=["Video Rendering"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "AI Shorts & Video Factory"}


@app.get("/api/download/{filename}")
async def download_video(filename: str):
    """Stream the final rendered MP4 to the client."""
    filepath = Path(settings.OUTPUT_DIR) / filename
    if not filepath.exists() or not filename.endswith(".mp4"):
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(
        path=str(filepath),
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
