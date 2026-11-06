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
    RESEND_APIKEY: str = os.getenv("RESEND_APIKEY", "")
    HUMAND_API_URL: str = os.getenv("HUMAND_API_URL", "https://api-prod.humand.co/public/api/v1")
    HUMAND_API_KEY: str = os.getenv("HUMAND_API_KEY", "")
    # Segundos que se cachean, en memoria, los datos de autoridad que se leen de
    # Odoo (user_id del empleado, proyectos que gerencia, aprobadores) en las
    # vistas de lectura. 0 la desactiva. Validar/borrar nunca la usan.
    AUTHZ_CACHE_TTL_SECONDS: int = int(os.getenv("AUTHZ_CACHE_TTL_SECONDS", "60"))

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar variables extra del .env


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
