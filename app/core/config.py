from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


class Settings(BaseSettings):
    EMAIL_USER: str = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar variables extra del .env


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
