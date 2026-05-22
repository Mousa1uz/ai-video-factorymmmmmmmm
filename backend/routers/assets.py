"""
Asset Generation Router
Handles image generation (Gemini/HuggingFace fallback) and audio (ElevenLabs/EdgeTTS fallback)
"""

import logging
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from services.image_service import ImageService
from services.audio_service import AudioService

logger = logging.getLogger(__name__)
router = APIRouter()
image_svc = ImageService()
audio_svc = AudioService()


class SceneAssetRequest(BaseModel):
    session_id: str
    scene_index: int
    image_prompt: str
    narration: str
    voice_id: Optional[str] = None          # ElevenLabs voice ID
    edge_tts_voice: Optional[str] = None    # Edge-TTS voice name
    tts_provider: str = "elevenlabs"        # "elevenlabs" | "edge"
    language: str = "en"


class BatchAssetRequest(BaseModel):
    session_id: str
    scenes: List[SceneAssetRequest]


class SceneAssetResponse(BaseModel):
    scene_index: int
    image_url: str       # served from /static/previews/
    audio_url: str       # served from /static/previews/
    audio_duration: float
    image_provider: str  # "gemini" | "huggingface"
    audio_provider: str  # "elevenlabs" | "edge"
    success: bool
    error: Optional[str] = None


@router.post("/generate-scene", response_model=SceneAssetResponse)
async def generate_scene_assets(req: SceneAssetRequest):
    """Generate image + audio for a single scene."""
    try:
        image_result = await image_svc.generate_image(
            session_id=req.session_id,
            scene_index=req.scene_index,
            prompt=req.image_prompt,
        )
        audio_result = await audio_svc.generate_audio(
            session_id=req.session_id,
            scene_index=req.scene_index,
            text=req.narration,
            provider=req.tts_provider,
            voice_id=req.voice_id,
            edge_voice=req.edge_tts_voice,
            language=req.language,
        )
        return SceneAssetResponse(
            scene_index=req.scene_index,
            image_url=image_result["url"],
            audio_url=audio_result["url"],
            audio_duration=audio_result["duration"],
            image_provider=image_result["provider"],
            audio_provider=audio_result["provider"],
            success=True,
        )
    except Exception as e:
        logger.error(f"Scene {req.scene_index} asset generation failed: {e}")
        return SceneAssetResponse(
            scene_index=req.scene_index,
            image_url="",
            audio_url="",
            audio_duration=0,
            image_provider="none",
            audio_provider="none",
            success=False,
            error=str(e),
        )


@router.post("/generate-batch")
async def generate_batch_assets(req: BatchAssetRequest):
    """Generate all scene assets in parallel (with concurrency limit)."""
    semaphore = asyncio.Semaphore(4)  # max 4 concurrent requests

    async def bounded(scene: SceneAssetRequest):
        async with semaphore:
            return await generate_scene_assets(scene)

    tasks = [bounded(scene) for scene in req.scenes]
    results = await asyncio.gather(*tasks)
    return {"session_id": req.session_id, "results": results}


@router.get("/voices")
async def list_voices():
    """Return available voices for both providers."""
    elevenlabs_voices = [
        {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female", "accent": "American"},
        {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "gender": "female", "accent": "American"},
        {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female", "accent": "American"},
        {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "gender": "male", "accent": "American"},
        {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "gender": "female", "accent": "American"},
        {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "gender": "male", "accent": "American"},
        {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "gender": "male", "accent": "American"},
        {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male", "accent": "American"},
    ]
    edge_voices = [
        {"id": "en-US-AriaNeural", "name": "Aria (English)", "gender": "female", "lang": "en"},
        {"id": "en-US-GuyNeural", "name": "Guy (English)", "gender": "male", "lang": "en"},
        {"id": "en-GB-SoniaNeural", "name": "Sonia (British)", "gender": "female", "lang": "en"},
        {"id": "ar-EG-SalmaNeural", "name": "Salma (Arabic)", "gender": "female", "lang": "ar"},
        {"id": "ar-SA-ZariyahNeural", "name": "Zariyah (Arabic)", "gender": "female", "lang": "ar"},
        {"id": "ar-EG-ShakirNeural", "name": "Shakir (Arabic)", "gender": "male", "lang": "ar"},
    ]
    return {"elevenlabs": elevenlabs_voices, "edge_tts": edge_voices}
