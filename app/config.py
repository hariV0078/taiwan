from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str = "sqlite:///./circularx.db"
    SUPABASE_DATABASE_URL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    CHROMA_PERSIST_PATH: str = "./chroma_store"
    DPP_STORAGE_PATH: str = "./storage/dpps"
    PLATFORM_FEE_PCT: float = 2.0
    AUTH_BYPASS: bool = False
    TEST_USER_COMPANY: str = "Test Company"
    TEST_USER_COUNTRY: str = "IN"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
