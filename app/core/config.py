from functools import lru_cache
from pydantic import BaseSettings


class Settings(BaseSettings):
    project_name: str = "Цифровой класс"
    database_url: str = "sqlite:///./app.db"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    files_dir: str = "uploads"
    files_base_url: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
