"""
Image Generation Service
Primary: Google Gemini Imagen 3.0
Fallback: HuggingFace Inference API (FLUX.1-schnell / SDXL)
Auto-fallback on 503 / rate-limit errors
"""

import logging
import asyncio
import base64
import httpx
from pathlib import Path
import google.generativeai as genai
from utils.config import settings

logger = logging.getLogger(__name__)

HF_MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
]
HF_API_URL = "https://api-inference.huggingface.co/models/{model}"


class ImageService:
    def __init__(self):
        self.output_dir = Path("static/previews")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.imagen_model = genai.ImageGenerationModel("imagen-3.0-generate-002")
        else:
            self.imagen_model = None
            logger.warning("GEMINI_API_KEY not set — falling back to HuggingFace only")

    def _image_path(self, session_id: str, scene_index: int) -> Path:
        return self.output_dir / f"{session_id}_scene_{scene_index:03d}.jpg"

    async def generate_image(self, session_id: str, scene_index: int, prompt: str) -> dict:
        """Try Gemini Imagen first, then HuggingFace fallback."""
        path = self._image_path(session_id, scene_index)

        # Try Gemini Imagen 3.0
        if self.imagen_model:
            try:
                result = await asyncio.to_thread(self._gemini_imagen, prompt)
                path.write_bytes(result)
                logger.info(f"  🖼 Scene {scene_index}: Gemini Imagen ✓")
                return {
                    "url": f"/static/previews/{path.name}",
                    "path": str(path),
                    "provider": "gemini",
                }
            except Exception as e:
                logger.warning(f"  ⚠ Gemini Imagen failed (scene {scene_index}): {e} → trying HF")

        # Fallback: HuggingFace
        for model in HF_MODELS:
            try:
                result = await self._hf_inference(prompt, model)
                path.write_bytes(result)
                logger.info(f"  🖼 Scene {scene_index}: HuggingFace ({model.split('/')[1]}) ✓")
                return {
                    "url": f"/static/previews/{path.name}",
                    "path": str(path),
                    "provider": "huggingface",
                }
            except Exception as e:
                logger.warning(f"  ⚠ HF model {model} failed: {e}")

        # Last resort: generate a placeholder gradient image
        placeholder = self._generate_placeholder(scene_index)
        path.write_bytes(placeholder)
        logger.warning(f"  ⚠ Scene {scene_index}: Using placeholder image")
        return {
            "url": f"/static/previews/{path.name}",
            "path": str(path),
            "provider": "placeholder",
        }

    def _gemini_imagen(self, prompt: str) -> bytes:
        enhanced = (
            f"{prompt}, cinematic 9:16 vertical format, ultra-detailed, "
            "professional photography, dramatic lighting, 8K quality"
        )
        response = self.imagen_model.generate_images(
            prompt=enhanced,
            number_of_images=1,
            aspect_ratio="9:16",
            safety_filter_level="block_some",
            person_generation="allow_adult",
        )
        # Returns bytes directly
        return response.images[0]._image_bytes

    async def _hf_inference(self, prompt: str, model: str) -> bytes:
        headers = {}
        if settings.HUGGINGFACE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.HUGGINGFACE_TOKEN}"
        payload = {
            "inputs": f"{prompt}, vertical 9:16, cinematic, ultra detailed, high quality",
            "parameters": {"width": 576, "height": 1024, "num_inference_steps": 4},
        }
        url = HF_API_URL.format(model=model)
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 503:
                raise RuntimeError(f"HF model {model} is loading (503)")
            if r.status_code != 200:
                raise RuntimeError(f"HF API error {r.status_code}: {r.text[:200]}")
            return r.content

    def _generate_placeholder(self, scene_index: int) -> bytes:
        """Generate a simple colored placeholder as JPEG bytes."""
        from PIL import Image, ImageDraw
        import io
        colors = [
            (15, 23, 42), (30, 27, 75), (20, 33, 61),
            (17, 24, 39), (24, 24, 27), (7, 89, 133),
        ]
        color = colors[scene_index % len(colors)]
        img = Image.new("RGB", (576, 1024), color)
        draw = ImageDraw.Draw(img)
        draw.text((288, 512), f"Scene {scene_index + 1}", fill=(100, 100, 120), anchor="mm")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
