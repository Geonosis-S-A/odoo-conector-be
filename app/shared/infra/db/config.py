import os
from dotenv import load_dotenv

load_dotenv()


class DatabaseSettings:
    # Entorno actual (local, staging, production)
    ENV = os.getenv("ENV", "LOCAL")

    print(f"ENV: {ENV}")
    # Base de datos para desarrollo
    if ENV == "LOCAL":
        DATABASE_URL = "sqlite:///./app.db"
    else:
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    print(f"DATABASE_URL: {DATABASE_URL}")

    # URL Para migraciones
    MIGRATION_DATABASE_URL = os.getenv(
        "MIGRATION_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/postgres",
    )

    # Base de datos para pruebas
    TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")

    def validate_database_url(self):
        # Si no estamos en local y la base de datos es SQLite, lanzar un error
        if self.ENV != "LOCAL" and self.DATABASE_URL.startswith("sqlite"):
            raise ValueError(
                f"SQLite no está permitido en el entorno '{self.ENV}'. "
                "Por favor, configure una base de datos válida para staging o production."
            )
        if self.ENV in ("STAGING", "PROD") and not self.DATABASE_URL.startswith(
            "postgresql"
        ):
            raise ValueError(
                f"En el entorno '{self.ENV}' solo se permite PostgreSQL. "
                "Por favor, configure una URL que comience con 'postgresql://'."
            )


settings = DatabaseSettings()
settings.validate_database_url()  # Validar la configuración al inicializar
