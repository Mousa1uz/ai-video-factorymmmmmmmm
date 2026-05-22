"""
Audio Generation Service
Primary: ElevenLabs API (Free Tier) — realistic voices
Fallback: Edge-TTS (Microsoft) — unlimited, supports Arabic & English
"""

import logging
import asyncio
import httpx
import edge_tts
from pathlib import Path
from utils.config import settings

logger = logging.getLogger(__name__)

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class AudioService:
    def __init__(self):
        self.output_dir = Path("static/previews")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _audio_path(self, session_id: str, scene_index: int) -> Path:
        return self.output_dir / f"{session_id}_audio_{scene_index:03d}.mp3"

    async def generate_audio(
        self,
        session_id: str,
        scene_index: int,
        text: str,
        provider: str = "elevenlabs",
        voice_id: str = None,
        edge_voice: str = None,
        language: str = "en",
    ) -> dict:
        path = self._audio_path(session_id, scene_index)

        if provider == "elevenlabs" and settings.ELEVENLABS_API_KEY:
            try:
                audio_bytes = await self._elevenlabs_tts(
                    text=text,
                    voice_id=voice_id or settings.DEFAULT_ELEVENLABS_VOICE_ID,
                )
                path.write_bytes(audio_bytes)
                duration = await self._get_mp3_duration(path)
                logger.info(f"  🔊 Scene {scene_index}: ElevenLabs ✓ ({duration:.1f}s)")
                return {
                    "url": f"/static/previews/{path.name}",
                    "path": str(path),
                    "duration": duration,
                    "provider": "elevenlabs",
                }
            except Exception as e:
                logger.warning(f"  ⚠ ElevenLabs failed (scene {scene_index}): {e} → Edge-TTS")

        # Fallback / direct Edge-TTS
        try:
            voice = edge_voice or self._default_edge_voice(language)
            await self._edge_tts(text=text, voice=voice, output_path=str(path))
            duration = await self._get_mp3_duration(path)
            logger.info(f"  🔊 Scene {scene_index}: Edge-TTS ✓ ({duration:.1f}s)")
            return {
                "url": f"/static/previews/{path.name}",
                "path": str(path),
                "duration": duration,
                "provider": "edge",
            }
        except Exception as e:
            logger.error(f"  ✗ All TTS providers failed for scene {scene_index}: {e}")
            raise

    async def _elevenlabs_tts(self, text: str, voice_id: str) -> bytes:
        url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
        headers = {
            "xi-api-key": settings.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.4},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 429:
                raise RuntimeError("ElevenLabs rate limit hit")
            if r.status_code != 200:
                raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:200]}")
            return r.content

    async def _edge_tts(self, text: str, voice: str, output_path: str):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    def _default_edge_voice(self, language: str) -> str:
        ar_voices = {
            "ar": "ar-EG-SalmaNeural",
            "en": settings.DEFAULT_EDGE_TTS_VOICE,
        }
        return ar_voices.get(language, settings.DEFAULT_EDGE_TTS_VOICE)

    async def _get_mp3_duration(self, path: Path) -> float:
        """Estimate duration from MP3 file size (fast approximation)."""
        try:
            # ~128kbps CBR: bytes / (128000 / 8) = seconds
            size = path.stat().st_size
            return max(1.0, size / 16000)
        except Exception:
            return 6.0
