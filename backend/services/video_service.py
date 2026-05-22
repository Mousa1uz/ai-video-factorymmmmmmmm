"""
Video Compilation Service
Uses MoviePy to compile scenes into a final MP4:
- Dynamic Ken Burns effect (zoom/pan) per scene
- Audio-locked clip durations
- Centered subtitle overlay per scene
- 9:16 vertical format (Shorts/Reels/TikTok ready)
"""

import logging
import asyncio
import uuid
import random
import numpy as np
from pathlib import Path
from typing import List, Callable, Optional
from PIL import Image, ImageDraw, ImageFont

from utils.config import settings

logger = logging.getLogger(__name__)

# Ken Burns motion presets
KB_PRESETS = [
    {"type": "zoom_in",   "scale_start": 1.0,  "scale_end": 1.12, "x": 0.0,  "y": 0.0},
    {"type": "zoom_out",  "scale_start": 1.12, "scale_end": 1.0,  "x": 0.0,  "y": 0.0},
    {"type": "pan_right", "scale_start": 1.08, "scale_end": 1.08, "x": -0.04, "y": 0.0},
    {"type": "pan_left",  "scale_start": 1.08, "scale_end": 1.08, "x": 0.04,  "y": 0.0},
    {"type": "pan_up",    "scale_start": 1.08, "scale_end": 1.08, "x": 0.0,  "y": 0.04},
    {"type": "pan_down",  "scale_start": 1.08, "scale_end": 1.08, "x": 0.0,  "y": -0.04},
]


class VideoService:
    def __init__(self):
        self.output_dir = Path(settings.OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def compile_video(
        self,
        session_id: str,
        title: str,
        scenes: list,
        subtitle_style: str = "default",
        resolution: str = "1080x1920",
        fps: int = 30,
        progress_cb: Optional[Callable] = None,
    ) -> str:
        return await asyncio.to_thread(
            self._compile_sync,
            session_id, title, scenes, subtitle_style, resolution, fps, progress_cb
        )

    def _compile_sync(self, session_id, title, scenes, subtitle_style, resolution, fps, progress_cb):
        from moviepy.editor import (
            VideoFileClip, ImageClip, AudioFileClip, concatenate_videoclips,
            CompositeVideoClip, TextClip, ColorClip
        )

        w_str, h_str = resolution.split("x")
        W, H = int(w_str), int(h_str)

        output_filename = f"video_{session_id}_{uuid.uuid4().hex[:8]}.mp4"
        output_path = str(self.output_dir / output_filename)

        clips = []
        total = len(scenes)

        for i, scene in enumerate(scenes):
            pct = int(10 + (i / total) * 75)
            if progress_cb:
                progress_cb(pct)

            try:
                clip = self._build_scene_clip(
                    scene=scene, W=W, H=H, fps=fps,
                    subtitle_style=subtitle_style, scene_idx=i
                )
                clips.append(clip)
                logger.info(f"  🎬 Compiled scene {i+1}/{total} ({clip.duration:.1f}s)")
            except Exception as e:
                logger.error(f"  ✗ Scene {i+1} compile error: {e} — using fallback")
                fallback = self._fallback_clip(scene, W, H, fps)
                clips.append(fallback)

        if progress_cb:
            progress_cb(88)

        final = concatenate_videoclips(clips, method="compose")

        if progress_cb:
            progress_cb(92)

        final.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=4,
            logger=None,
        )

        if progress_cb:
            progress_cb(99)

        final.close()
        for c in clips:
            c.close()

        return output_path

    def _build_scene_clip(self, scene, W, H, fps, subtitle_style, scene_idx):
        from moviepy.editor import (
            ImageClip, AudioFileClip, CompositeVideoClip, TextClip
        )

        # Load audio to determine duration
        audio_path = scene.get("audio_path") or scene.audio_path
        image_path = scene.get("image_path") or scene.image_path
        narration = scene.get("narration") or scene.narration
        audio_duration = float(scene.get("audio_duration") or scene.audio_duration or 6.0)

        try:
            audio = AudioFileClip(audio_path)
            duration = audio.duration
        except Exception:
            audio = None
            duration = audio_duration

        # Load and resize image
        try:
            img = Image.open(image_path).convert("RGB")
        except Exception:
            img = Image.new("RGB", (W, H), (15, 23, 42))

        img_resized = self._cover_resize(img, W, H)
        img_array = np.array(img_resized)

        # Ken Burns effect
        preset = KB_PRESETS[scene_idx % len(KB_PRESETS)]
        video_clip = self._apply_ken_burns(img_array, duration, fps, preset, W, H)

        # Subtitle overlay
        sub_clip = self._build_subtitle(narration, W, H, duration, subtitle_style)

        # Compose
        layers = [video_clip]
        if sub_clip:
            layers.append(sub_clip)

        composed = CompositeVideoClip(layers, size=(W, H))

        if audio:
            composed = composed.set_audio(audio)

        return composed.set_duration(duration)

    def _apply_ken_burns(self, img_array, duration, fps, preset, W, H):
        from moviepy.editor import VideoClip

        s_start = preset["scale_start"]
        s_end = preset["scale_end"]
        x_drift = preset["x"]
        y_drift = preset["y"]

        def make_frame(t):
            progress = t / max(duration, 0.001)
            scale = s_start + (s_end - s_start) * progress

            ih, iw = img_array.shape[:2]
            new_w = int(iw * scale)
            new_h = int(ih * scale)

            # Center + drift offset
            cx = int((iw - new_w) / 2 + x_drift * iw * progress)
            cy = int((ih - new_h) / 2 + y_drift * ih * progress)

            cx = max(0, min(iw - new_w, cx + iw // 2 - new_w // 2))
            cy = max(0, min(ih - new_h, cy + ih // 2 - new_h // 2))

            try:
                cropped = img_array[cy:cy+new_h, cx:cx+new_w]
                from PIL import Image as PILImage
                resized = np.array(
                    PILImage.fromarray(cropped).resize((W, H), PILImage.LANCZOS)
                )
                return resized
            except Exception:
                return img_array[:H, :W]

        return VideoClip(make_frame, duration=duration)

    def _build_subtitle(self, text, W, H, duration, style):
        """Render stylized centered subtitle strip at the bottom of frame."""
        try:
            from moviepy.editor import TextClip

            font_size = 52 if style == "bold" else 44
            color = "white"
            stroke_color = "black"
            stroke_width = 3 if style == "bold" else 2

            # Wrap text
            words = text.split()
            lines, current = [], []
            for w in words:
                current.append(w)
                if len(" ".join(current)) > 32:
                    lines.append(" ".join(current[:-1]))
                    current = [w]
            if current:
                lines.append(" ".join(current))
            wrapped = "\n".join(lines[-3:])  # max 3 lines

            clip = (
                TextClip(
                    wrapped,
                    fontsize=font_size,
                    color=color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    font="Arial-Bold",
                    method="caption",
                    size=(W - 80, None),
                    align="center",
                )
                .set_position(("center", H - 280))
                .set_duration(duration)
            )
            return clip
        except Exception as e:
            logger.warning(f"Subtitle generation failed: {e}")
            return None

    def _cover_resize(self, img: Image.Image, W: int, H: int) -> Image.Image:
        """Resize image to cover W x H maintaining aspect ratio."""
        iw, ih = img.size
        scale = max(W / iw, H / ih) * 1.15  # slight overscan for Ken Burns
        new_w, new_h = int(iw * scale), int(ih * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - W) // 2
        top = (new_h - H) // 2
        return img.crop((left, top, left + W, top + H))

    def _fallback_clip(self, scene, W, H, fps):
        from moviepy.editor import ColorClip
        duration = float(getattr(scene, "audio_duration", None) or scene.get("audio_duration", 6))
        return ColorClip(size=(W, H), color=[15, 23, 42], duration=duration)
