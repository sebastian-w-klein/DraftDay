from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DraftDay API"
    app_env: str = "dev"
    app_port: int = 8000
    enable_draft_intelligence: bool = Field(default=True, alias="ENABLE_DRAFT_INTELLIGENCE")
    enable_org_intelligence: bool = Field(default=True, alias="ENABLE_ORG_INTELLIGENCE")
    database_url: str = Field(
        default="postgresql+psycopg://draftday:draftday@localhost:5432/draftday",
        alias="DATABASE_URL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
