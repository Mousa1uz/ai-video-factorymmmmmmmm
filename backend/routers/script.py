"""
Script Generation Router
Handles Mode A (AI topic → script) and Mode B (manual script → scenes)
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter()
gemini = GeminiService()


class ScriptRequest(BaseModel):
    mode: str  # "ai" | "manual"
    topic: Optional[str] = None
    manual_script: Optional[str] = None
    duration_minutes: float = 1.0  # 1.0, 1.5, 2.0, 2.5, 3.0
    language: str = "en"  # "en" | "ar"


class Scene(BaseModel):
    index: int
    narration: str
    image_prompt: str
    duration_hint: float  # estimated seconds


class ScriptResponse(BaseModel):
    title: str
    total_scenes: int
    estimated_duration: float
    scenes: list[Scene]


@router.post("/generate", response_model=ScriptResponse)
async def generate_script(req: ScriptRequest):
    """Generate or parse script into scenes with image prompts."""
    if req.mode == "ai":
        if not req.topic:
            raise HTTPException(status_code=400, detail="Topic is required for AI mode")
        result = await gemini.generate_script_from_topic(
            topic=req.topic,
            duration_minutes=req.duration_minutes,
            language=req.language,
        )
    elif req.mode == "manual":
        if not req.manual_script:
            raise HTTPException(status_code=400, detail="Script text is required for manual mode")
        result = await gemini.parse_manual_script(
            script=req.manual_script,
            duration_minutes=req.duration_minutes,
            language=req.language,
        )
    else:
        raise HTTPException(status_code=400, detail="Mode must be 'ai' or 'manual'")

    return result
