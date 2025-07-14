import os
from typing import Optional, TypedDict, cast
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
import xmlrpc.client


class OdooConnection(TypedDict):
    uid: int
    models: xmlrpc.client.ServerProxy
    ODOO_DB: str
    ODOO_PASSWORD: str


def get_odoo_credentials() -> dict[str, str]:
    """Obtiene las credenciales de Odoo según el entorno actual.

    Returns:
        dict: Diccionario con las credenciales de Odoo

    Raises:
        ValueError: Si alguna variable de entorno requerida no está definida
    """
    load_dotenv()
    env = os.getenv("ENVIRONMENT", "local").lower()

    def get_env_var(name: str) -> str:
        # Intentar obtener la variable específica del entorno
        env_specific = os.getenv(f"{env.upper()}_{name}")
        if env_specific:
            return env_specific

        # Si no existe, usar la variable base
        value = os.getenv(name)
        if not value:
            raise ValueError(f"Variable de entorno {name} no definida")

        return value

    return {
        "url": get_env_var("ODOO_URL"),
        "db": get_env_var("ODOO_DB"),
        "username": get_env_var("ODOO_USERNAME"),
        "password": get_env_var("ODOO_PASSWORD"),
    }


class OdooClient:
    """Cliente para la conexión con Odoo."""

    def __init__(self) -> None:
        credentials = get_odoo_credentials()
        self.url = credentials["url"]
        self.db = credentials["db"]
        self.username = credentials["username"]
        self.password = credentials["password"]

        # Inicializar atributos de conexión
        self._uid: Optional[int] = None
        self._models: Optional[xmlrpc.client.ServerProxy] = None
        self._common: Optional[xmlrpc.client.ServerProxy] = None

    @property
    def uid(self) -> Optional[int]:
        return self._uid

    @uid.setter
    def uid(self, value: int) -> None:
        self._uid = value

    @property
    def models(self) -> Optional[xmlrpc.client.ServerProxy]:
        return self._models

    @models.setter
    def models(self, value: xmlrpc.client.ServerProxy) -> None:
        self._models = value

    @property
    def common(self) -> Optional[xmlrpc.client.ServerProxy]:
        return self._common

    @common.setter
    def common(self, value: xmlrpc.client.ServerProxy) -> None:
        self._common = value

    def authenticate(self) -> int:
        """Autentica el usuario con Odoo y establece el UID.

        Returns:
            int: El UID del usuario autenticado

        Raises:
            HTTPException: Si hay un error en la autenticación
        """
        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self.common = common

            uid = common.authenticate(self.db, self.username, self.password, {})
            if not uid:
                raise Exception("Error de autenticación con Odoo")

            self.uid = cast(int, uid)
            return cast(int, uid)
        except Exception as e:
            raise HTTPException(
                status_code=401, detail=f"Error de autenticación: {str(e)}"
            )

    def get_connection(self) -> OdooConnection:
        """Obtiene la conexión a Odoo, autenticando si es necesario.

        Returns:
            OdooConnection: Diccionario tipado con los datos de conexión

        Raises:
            HTTPException: Si hay un error al conectar con Odoo
        """
        try:
            if not self.uid:
                self.authenticate()

            if not self.models:
                self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

            if not self.uid or not self.models:
                raise Exception("No se pudo establecer la conexión con Odoo")

            return OdooConnection(
                uid=self.uid,
                models=self.models,
                ODOO_DB=self.db,
                ODOO_PASSWORD=self.password,
            )
        except Exception as e:
            print("Error al conectar con Odoo: ", e)
            raise HTTPException(status_code=500, detail="Error al conectar con Odoo")


# Instancia global del cliente Odoo
odoo_client = OdooClient()


# Función de dependencia para mantener compatibilidad con el código existente
def get_odoo_connection() -> OdooConnection:
    return odoo_client.get_connection()


# Función de dependencia para FastAPI
async def get_odoo_connection_dependency() -> OdooConnection:
    """Función de dependencia para FastAPI que proporciona la conexión a Odoo."""
    try:
        return odoo_client.get_connection()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al establecer la conexión con Odoo: {str(e)}",
        )
