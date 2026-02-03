"""
Application configuration settings.
Loads environment variables and provides centralized configuration.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "AWB Management Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Database - AWB Editor PostgreSQL (read-only)
    AWB_DATABASE_HOST: str = "localhost"
    AWB_DATABASE_PORT: int = 5432
    AWB_DATABASE_NAME: str = "awb_editor"
    AWB_DATABASE_USER: str = "postgres"
    AWB_DATABASE_PASSWORD: str = ""
    
    # Internal database for users, logs, settings
    INTERNAL_DATABASE_URL: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    @property
    def awb_database_url(self) -> str:
        """Construct AWB database URL from components."""
        return (
            f"postgresql+psycopg://{self.AWB_DATABASE_USER}:{self.AWB_DATABASE_PASSWORD}"
            f"@{self.AWB_DATABASE_HOST}:{self.AWB_DATABASE_PORT}/{self.AWB_DATABASE_NAME}"
        )
    
    @property
    def awb_database_url_async(self) -> str:
        """Construct async AWB database URL (using psycopg async)."""
        return (
            f"postgresql+psycopg_async://{self.AWB_DATABASE_USER}:{self.AWB_DATABASE_PASSWORD}"
            f"@{self.AWB_DATABASE_HOST}:{self.AWB_DATABASE_PORT}/{self.AWB_DATABASE_NAME}"
        )
    
    @property
    def internal_db_url(self) -> str:
        """Get internal database URL or default to SQLite."""
        if self.INTERNAL_DATABASE_URL:
            return self.INTERNAL_DATABASE_URL
        return "sqlite:///./awb_platform.db"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

