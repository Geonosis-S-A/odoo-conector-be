import os
import time
from typing import Any

import httpx
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv


load_dotenv()

TENANT_ID = os.getenv("TENANT_ID", "")
CLIENT_ID = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
SITE_ID = os.getenv("SITE_ID", "")
ITEM_ID = os.getenv("ITEM_ID", "")
GANTT_SITE_ID = os.getenv("GANTT_SITE_ID", "")
GANTT_ITEM_ID = os.getenv("GANTT_ITEM_ID", "")

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
CACHE_TTL_SECONDS = 300  # 5 minutos

_cache: dict[str, dict[str, Any]] = {}


def _get_cached(key: str) -> list[dict] | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry["timestamp"]) < CACHE_TTL_SECONDS:
        return entry["data"]
    return None


def _set_cached(key: str, data: list[dict]) -> None:
    _cache[key] = {"data": data, "timestamp": time.time()}


def _rows_to_dicts(values: list[list]) -> list[dict]:
    if not values or len(values) < 2:
        return []
    headers = [str(h).strip() for h in values[0]]
    return [
        {headers[i]: row[i] if i < len(row) else None for i in range(len(headers))}
        for row in values[1:]
    ]


class GraphExcelClient:
    def __init__(
        self,
        site_id: str | None = None,
        item_id: str | None = None,
    ) -> None:
        self._credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )
        self.site_id = site_id if site_id is not None else SITE_ID
        self.item_id = item_id if item_id is not None else ITEM_ID
        self._drive_id: str | None = None

    def _cache_key(self, sheet_name: str) -> str:
        return f"{self.site_id}:{self.item_id}:{sheet_name}"

    def _get_token(self) -> str:
        token = self._credential.get_token("https://graph.microsoft.com/.default")
        return token.token

    def _get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    async def _get_drive_id(self) -> str:
        if self._drive_id:
            return self._drive_id

        # SITE_ID tiene formato "hostname,spsite-id,spweb-id"
        # Separar para usar /sites/{hostname}:/sites/{path} o lookup por IDs
        parts = self.site_id.split(",")
        if len(parts) == 3:
            hostname, site_collection_id, web_id = [p.strip() for p in parts]
            url = f"{GRAPH_BASE_URL}/sites/{hostname},{site_collection_id},{web_id}/drive"
        else:
            url = f"{GRAPH_BASE_URL}/sites/{self.site_id}/drive"

        headers = self._get_headers()

        async with httpx.AsyncClient() as http:
            response = await http.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            raise Exception(
                f"Error obteniendo drive del site ({response.status_code}): {response.text}"
            )

        self._drive_id = response.json()["id"]
        return self._drive_id

    async def get_worksheet_data(self, sheet_name: str) -> list[dict]:
        cache_key = self._cache_key(sheet_name)
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        drive_id = await self._get_drive_id()
        url = (
            f"{GRAPH_BASE_URL}/drives/{drive_id}"
            f"/items/{self.item_id}"
            f"/workbook/worksheets('{sheet_name}')/usedRange"
        )

        async with httpx.AsyncClient() as http:
            response = await http.get(url, headers=self._get_headers(), timeout=30)

        if response.status_code != 200:
            raise Exception(
                f"Graph API error {response.status_code} para hoja '{sheet_name}': {response.text}"
            )

        result = response.json()
        values = result.get("values", [])
        data = _rows_to_dicts(values)
        _set_cached(cache_key, data)
        return data


_kpi_graph_client: GraphExcelClient | None = None
_gantt_graph_client: GraphExcelClient | None = None


def get_graph_excel_client() -> GraphExcelClient:
    global _kpi_graph_client
    if _kpi_graph_client is None:
        _kpi_graph_client = GraphExcelClient()
    return _kpi_graph_client


def get_graph_excel_gantt_client() -> GraphExcelClient:
    global _gantt_graph_client
    if _gantt_graph_client is None:
        if not (GANTT_ITEM_ID or "").strip():
            raise RuntimeError(
                "GANTT_ITEM_ID debe estar definido en el entorno (id del archivo Base Gantt.xlsx en Graph)."
            )
        site = (GANTT_SITE_ID or "").strip() or SITE_ID
        _gantt_graph_client = GraphExcelClient(
            site_id=site,
            item_id=GANTT_ITEM_ID.strip(),
        )
    return _gantt_graph_client
