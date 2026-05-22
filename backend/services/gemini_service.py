"""
Gemini Service
Handles script generation (Mode A) and script parsing (Mode B)
Uses Google Gemini 2.5 Flash via google-generativeai SDK
"""

import json
import logging
import re
from typing import Optional
import google.generativeai as genai
from utils.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY not set — script generation will fail")

    def _scenes_for_duration(self, duration_minutes: float) -> int:
        """Map duration to scene count (approx 6s per scene)."""
        return max(10, min(30, int(duration_minutes * 60 / 6)))

    async def generate_script_from_topic(
        self, topic: str, duration_minutes: float, language: str = "en"
    ) -> dict:
        scene_count = self._scenes_for_duration(duration_minutes)
        lang_instruction = "Arabic" if language == "ar" else "English"

        prompt = f"""You are a world-class short-form video scriptwriter.
Create a highly engaging, story-driven video script about: "{topic}"

Requirements:
- Language: {lang_instruction}
- Total scenes: exactly {scene_count}
- Each scene narration: 1-3 punchy sentences (fits ~5-8 seconds of voiceover)
- Style: Cinematic, emotionally compelling, educational or entertaining
- Each image prompt: hyper-detailed, photorealistic or cinematic style, English always

Return ONLY valid JSON (no markdown, no backticks):
{{
  "title": "Video title here",
  "scenes": [
    {{
      "index": 1,
      "narration": "Scene narration text in {lang_instruction}",
      "image_prompt": "Hyper-detailed English image prompt: [subject], [environment], [lighting], [style], [mood], 8K, cinematic, photorealistic",
      "duration_hint": 6.5
    }}
  ]
}}"""

        return await self._call_gemini(prompt, scene_count, duration_minutes)

    async def parse_manual_script(
        self, script: str, duration_minutes: float, language: str = "en"
    ) -> dict:
        scene_count = self._scenes_for_duration(duration_minutes)

        prompt = f"""You are a professional video editor and AI director.
Parse the following script into exactly {scene_count} sequential scenes for a short-form video.
Generate a cinematic image prompt for each scene.

Script:
---
{script[:8000]}
---

Return ONLY valid JSON (no markdown, no backticks):
{{
  "title": "Derived title from script",
  "scenes": [
    {{
      "index": 1,
      "narration": "Scene narration (direct quote or paraphrase from script)",
      "image_prompt": "Hyper-detailed English cinematic image prompt for this scene moment",
      "duration_hint": 6.0
    }}
  ]
}}

Rules:
- Split the script evenly across {scene_count} scenes
- Image prompts must always be in English, highly descriptive, 8K cinematic style
- Preserve the original language of narration
- duration_hint should realistically match text length (words / 2.5 = seconds)"""

        return await self._call_gemini(prompt, scene_count, duration_minutes)

    async def _call_gemini(self, prompt: str, scene_count: int, duration_minutes: float) -> dict:
        if not self.model:
            raise RuntimeError("Gemini API key not configured")
        try:
            response = self.model.generate_content(prompt)
            raw = response.text.strip()

            # Strip possible markdown fences
            raw = re.sub(r"^```json\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            data = json.loads(raw)
            scenes = data.get("scenes", [])

            return {
                "title": data.get("title", "Untitled Video"),
                "total_scenes": len(scenes),
                "estimated_duration": sum(s.get("duration_hint", 6) for s in scenes),
                "scenes": scenes,
            }
        except json.JSONDecodeError as e:
            logger.error(f"Gemini JSON parse error: {e}\nRaw: {raw[:500]}")
            raise RuntimeError(f"Gemini returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
