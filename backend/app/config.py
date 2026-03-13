from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URI: str = "mongodb+srv://<user>:<password>@cluster.mongodb.net"
    DATABASE_NAME: str = "adaptive_testing"

    # Gemini
    GEMINI_API_KEY: str = ""

    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5500", "http://localhost:5500"]

    # IRT Config
    LEARNING_RATE: float = 0.3
    MAX_QUESTIONS: int = 10
    BASELINE_ABILITY: float = 0.5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
