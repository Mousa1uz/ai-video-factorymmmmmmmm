"""App-wide configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    HUGGINGFACE_TOKEN: str = ""

    APP_ENV: str = "development"
    MAX_SCENES: int = 30
    OUTPUT_DIR: str = "outputs"
    TEMP_DIR: str = "temp"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    DEFAULT_ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"
    DEFAULT_EDGE_TTS_VOICE: str = "en-US-AriaNeural"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
