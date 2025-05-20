import os


class DatabaseSettings:
    # Entorno actual (local, staging, production)
    ENV = os.getenv("ENV", "local")

    # Base de datos para desarrollo
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    # Base de datos para pruebas
    TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")

    def validate_database_url(self):
        # Si no estamos en local y la base de datos es SQLite, lanzar un error
        if self.ENV != "local" and self.DATABASE_URL.startswith("sqlite"):
            raise ValueError(
                f"SQLite no está permitido en el entorno '{self.ENV}'. "
                "Por favor, configure una base de datos válida para staging o production."
            )


settings = DatabaseSettings()
settings.validate_database_url()  # Validar la configuración al inicializar
