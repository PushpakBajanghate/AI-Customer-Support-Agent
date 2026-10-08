import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Search for .env file in project root or backend directory
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
backend_root = current_file.parent.parent

if (project_root / ".env").exists():
    load_dotenv(project_root / ".env")
elif (backend_root / ".env").exists():
    load_dotenv(backend_root / ".env")
else:
    load_dotenv()

class Settings(BaseSettings):
    """Application settings and configuration parameters."""
    APP_ENV: str = os.getenv("APP_ENV", "development")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))

    # LLM Settings (Configurable for Google Gemini or OpenAI)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_API_KEY: str = (
        os.getenv("LLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or ""
    )
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-1.5-flash")

    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/customer_support_db")

    # Vector DB (Qdrant)
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")

    # Security & JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "default_secret_key_change_in_production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
