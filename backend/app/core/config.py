from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Basic FastAPI application settings."""

    app_name: str = "AI-Powered Operating Intelligence Platform API"
    app_version: str = "0.1.0"
    environment: str = "development"


settings = Settings()