import os
from typing import Optional, TypedDict, cast
from dotenv import load_dotenv
from fastapi import HTTPException
import xmlrpc.client

class OdooConnection(TypedDict):
    uid: int
    models: xmlrpc.client.ServerProxy
    ODOO_DB: str
    ODOO_PASSWORD: str

class OdooClient:
    def __init__(self) -> None:
        # Cargar variables de entorno
        load_dotenv()
        
        # Inicializar variables de conexión
        self.url: str = os.getenv("ODOO_URL", "")
        self.db: str = os.getenv("ODOO_DB", "")
        self.username: str = os.getenv("ODOO_USERNAME", "")
        self.password: str = os.getenv("ODOO_PASSWORD", "")
        
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
            raise HTTPException(status_code=401, detail=f"Error de autenticación: {str(e)}")

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
                ODOO_PASSWORD=self.password
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al conectar con Odoo: {str(e)}")

# Instancia global del cliente Odoo
odoo_client: OdooClient = OdooClient()

# Función de dependencia para mantener compatibilidad con el código existente
def get_odoo_connection() -> OdooConnection:
    return odoo_client.get_connection()