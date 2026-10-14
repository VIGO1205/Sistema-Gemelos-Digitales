from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "M-6 Gemelo Digital API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/m6_gemelo_digital"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@db:5432/m6_gemelo_digital"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"

    # Security
    SECRET_KEY: str = "m6-super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    DEMO_ACCOUNTS_ENABLED: bool = False
    INITIAL_ADMIN_EMAIL: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""
    ENABLE_PUBLIC_REGISTRATION: bool = False

    # GROQ AI
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    GROQ_MAX_TOKENS: int = 2048
    GROQ_TEMPERATURE: float = 0.4

    # LangFlow Integration
    USE_LANGFLOW: bool = True
    LANGFLOW_URL: str = "http://host.docker.internal:7860"
    LANGFLOW_FLOW_ID: str = "b0fe7e2a-60aa-45ff-a714-14c4328a3172"
    LANGFLOW_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
