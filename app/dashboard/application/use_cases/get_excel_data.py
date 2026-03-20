import asyncio
import os

from app.shared.infra.external.microsoft.graph_client import GraphExcelClient

GANTT_SHEET_NAME = os.getenv("GANTT_SHEET_NAME", "base")


class GetExcelDataUseCase:
    SHEET_NAMES = ["Proyectos", "Horas", "Headcount"]

    def __init__(self, client: GraphExcelClient) -> None:
        self.client = client

    async def execute(self) -> dict[str, list[dict]]:
        proyectos, horas, headcount = await asyncio.gather(
            self.client.get_worksheet_data("Proyectos"),
            self.client.get_worksheet_data("Horas"),
            self.client.get_worksheet_data("Headcount"),
        )
        return {
            "proyectos": proyectos,
            "horas": horas,
            "headcount": headcount,
        }


class GetGanttExcelDataUseCase:
    """Lee la hoja configurada (por defecto 'base') del Excel Gantt en SharePoint."""

    def __init__(self, client: GraphExcelClient, sheet_name: str | None = None) -> None:
        self.client = client
        self.sheet_name = sheet_name or GANTT_SHEET_NAME

    async def execute(self) -> dict[str, list[dict]]:
        base = await self.client.get_worksheet_data(self.sheet_name)
        return {"base": base}
