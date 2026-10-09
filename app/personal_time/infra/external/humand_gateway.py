from typing import List, Optional
from datetime import date
import requests
from app.personal_time.domain.humand_gateway import HumandGateway
from app.personal_time.domain.models import HumandTimeOffRequest
from app.core.config import settings


class HumandAPIGateway(HumandGateway):
    """Implementación del gateway para conectarse con la API de HUMAND."""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """Inicializa el gateway con las credenciales de HUMAND.

        Args:
            api_url: URL base de la API de HUMAND (opcional, se toma de settings)
            api_key: API Key para autenticación (opcional, se toma de settings)
        """
        self.api_url = api_url or settings.HUMAND_API_URL
        self.api_key = api_key or settings.HUMAND_API_KEY
        self.base_endpoint = f"{self.api_url}/time-off/requests"

        # Validar que existan las credenciales
        if not self.api_key:
            raise ValueError("HUMAND_API_KEY no está configurado en las variables de entorno")

    def _get_headers(self) -> dict:
        """Genera los headers necesarios para las peticiones a HUMAND.

        Returns:
            dict: Headers con autenticación
        """
        return {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_all_timeoff_requests(
        self,
        page: int = 1,
        limit: int = 500,
        states: Optional[List[str]] = None,
        policy_type_ids: Optional[List[str]] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        resolution_from_date: Optional[date] = None,
        resolution_to_date: Optional[date] = None,
        created_at_since: Optional[date] = None,
    ) -> List[HumandTimeOffRequest]:
        """Obtiene todas las solicitudes de tiempo personal desde HUMAND.

        Args:
            page: Página para paginación (default: 1)
            limit: Límite de resultados por página (default: 50)
            states: Lista de estados para filtrar (ej: ["approved", "pending", "rejected"])
            policy_type_ids: Lista de IDs de tipos de política para filtrar
            from_date: Fecha de inicio del filtro
            to_date: Fecha de fin del filtro
            resolution_from_date: Fecha de inicio de resolución
            resolution_to_date: Fecha de fin de resolución
            created_at_since: Filtrar por fecha de creación desde

        Returns:
            List[HumandTimeOffRequest]: Lista de solicitudes de HUMAND

        Raises:
            Exception: Si hay un error al obtener las solicitudes de HUMAND
        """
        try:
            # Construir parámetros de la petición
            params: dict = {
                "page": page,
            }


            # Agregar filtros opcionales
            if states:
                params["states"] = ",".join(states)

            if policy_type_ids:
                params["policyTypeIds"] = ",".join(policy_type_ids)

            if from_date:
                params["fromDate"] = from_date.strftime("%Y-%m-%d")

            if to_date:
                params["toDate"] = to_date.strftime("%Y-%m-%d")

            if resolution_from_date:
                params["resolutionFromDate"] = resolution_from_date.strftime("%Y-%m-%d")

            if resolution_to_date:
                params["resolutionToDate"] = resolution_to_date.strftime("%Y-%m-%d")

            if created_at_since:
                params["createdAtSince"] = created_at_since.strftime("%Y-%m-%d")

            params["limit"] = limit

            # Realizar la petición a HUMAND
            response = requests.get(
                self.base_endpoint,
                params=params,
                headers=self._get_headers(),
                timeout=30,  # Timeout de 30 segundos
            )

            # Validar respuesta
            response.raise_for_status()

            # Parsear respuesta JSON
            data = response.json()

            # Extraer las solicitudes del response
            # La estructura puede variar, ajusta según la respuesta real de HUMAND
            requests_data = data.get("items", []) if isinstance(data, dict) else data

            # Validar que sea una lista
            if not isinstance(requests_data, list):
                raise Exception(
                    f"Respuesta inesperada de HUMAND API: se esperaba una lista, se recibió {type(requests_data)}"
                )

            # Convertir a modelos de dominio
            timeoff_requests = []
            for item in requests_data:
                try:
                    timeoff_request = HumandTimeOffRequest.from_humand_data(item)
                    timeoff_requests.append(timeoff_request)
                except Exception as e:
                    # Log el error pero continuar procesando otros registros
                    print(
                        f"Warning: Error procesando solicitud ID {item.get('id', 'unknown')}: {str(e)}"
                    )
                    continue

            return timeoff_requests

        except requests.exceptions.HTTPError as e:
            # Error HTTP (4xx, 5xx)
            status_code = e.response.status_code if e.response else "unknown"
            error_detail = ""
            try:
                error_detail = e.response.json() if e.response else {}
            except:
                error_detail = e.response.text if e.response else ""

            raise Exception(
                f"Error HTTP {status_code} al consultar HUMAND API: {error_detail}"
            )

        except requests.exceptions.Timeout:
            raise Exception("Timeout al conectar con HUMAND API (30s)")

        except requests.exceptions.ConnectionError:
            raise Exception("Error de conexión con HUMAND API. Verifica la URL y conectividad.")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error en la petición a HUMAND API: {str(e)}")

        except Exception as e:
            raise Exception(f"Error inesperado al obtener solicitudes desde HUMAND: {str(e)}")

    def get_all_timeoff_requests_paginated(
        self,
        states: Optional[List[str]] = None,
        policy_type_ids: Optional[List[str]] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        resolution_from_date: Optional[date] = None,
        resolution_to_date: Optional[date] = None,
        created_at_since: Optional[date] = None,
        limit: int = 500,
        max_pages: int = 100,
    ) -> List[HumandTimeOffRequest]:
        """Obtiene todas las solicitudes paginando automáticamente hasta obtener todos los resultados.

        Args:
            limit: Límite de resultados por página (default: 50)
            states: Lista de estados para filtrar
            policy_type_ids: Lista de IDs de tipos de política para filtrar
            from_date: Fecha de inicio del filtro
            to_date: Fecha de fin del filtro
            resolution_from_date: Fecha de inicio de resolución
            resolution_to_date: Fecha de fin de resolución
            created_at_since: Filtrar por fecha de creación desde
            max_pages: Número máximo de páginas a consultar (default: 100)

        Returns:
            List[HumandTimeOffRequest]: Lista completa de solicitudes de HUMAND

        Raises:
            Exception: Si hay un error al obtener las solicitudes de HUMAND
        """
        all_requests = []
        page = 1

        while page <= max_pages:
            try:
                requests_page = self.get_all_timeoff_requests(
                    page=page,
                    limit=limit,
                    states=states,
                    policy_type_ids=policy_type_ids,
                    from_date=from_date,
                    to_date=to_date,
                    resolution_from_date=resolution_from_date,
                    resolution_to_date=resolution_to_date,
                    created_at_since=created_at_since,
                )

                # Si no hay más resultados, terminar
                if not requests_page:
                    break

                all_requests.extend(requests_page)

                page += 1

            except Exception as e:
                print(f"Error obteniendo página {page}: {str(e)}")
                raise

        return all_requests

