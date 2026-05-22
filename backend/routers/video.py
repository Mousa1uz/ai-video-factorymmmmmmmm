"""
Video Rendering Router
Triggers cloud-side MoviePy compilation of the final MP4
"""

import logging
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from services.video_service import VideoService

logger = logging.getLogger(__name__)
router = APIRouter()
video_svc = VideoService()

render_jobs: dict = {}


class SceneRenderData(BaseModel):
    scene_index: int
    narration: str
    image_path: str
    audio_path: str
    audio_duration: float


class RenderRequest(BaseModel):
    session_id: str
    title: str
    scenes: List[SceneRenderData]
    subtitle_style: str = "default"
    resolution: str = "1080x1920"
    fps: int = 30


class RenderStatusResponse(BaseModel):
    session_id: str
    status: str
    progress: int
    download_url: Optional[str] = None
    error: Optional[str] = None


@router.post("/render", response_model=RenderStatusResponse)
async def render_video(req: RenderRequest, background_tasks: BackgroundTasks):
    render_jobs[req.session_id] = {"status": "queued", "progress": 0}

    async def do_render():
        try:
            render_jobs[req.session_id] = {"status": "processing", "progress": 5}
            output_path = await video_svc.compile_video(
                session_id=req.session_id,
                title=req.title,
                scenes=req.scenes,
                subtitle_style=req.subtitle_style,
                resolution=req.resolution,
                fps=req.fps,
                progress_cb=lambda p: render_jobs[req.session_id].update({"progress": p}),
            )
            filename = Path(output_path).name
            render_jobs[req.session_id] = {
                "status": "done",
                "progress": 100,
                "download_url": f"/api/download/{filename}",
            }
        except Exception as e:
            logger.error(f"Render failed for {req.session_id}: {e}")
            render_jobs[req.session_id] = {"status": "failed", "progress": 0, "error": str(e)}

    background_tasks.add_task(do_render)
    return RenderStatusResponse(session_id=req.session_id, status="queued", progress=0)


@router.get("/status/{session_id}", response_model=RenderStatusResponse)
async def get_render_status(session_id: str):
    job = render_jobs.get(session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")
    return RenderStatusResponse(session_id=session_id, **job)
