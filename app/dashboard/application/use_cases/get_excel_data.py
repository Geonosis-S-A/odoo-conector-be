import asyncio

from app.shared.infra.external.microsoft.graph_client import GraphExcelClient


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
