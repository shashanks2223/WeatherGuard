from pathlib import Path
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = ""
    LLM_PROVIDER: str = "mock"
    LLM_MODEL: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = ""
    POLICIES_DIR: Path = Path(__file__).resolve().parent / "policies"
    FRONTEND_URL: str = ""

    @field_validator("FRONTEND_URL", mode="after")
    @classmethod
    def normalize_frontend_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        if isinstance(v, str):
            return [origin.strip().rstrip("/") for origin in v.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
