"""Tests de regresión para VT-12 (GEO-1388) sobre las tools del agente IA
que aceptan texto libre (`description`) y producen el `pending_confirmation`.

Estos tests verifican que la validación de seguridad se ejecuta ANTES de
cualquier conexión a Odoo, de modo que:
- El LLM recibe un error JSON inmediato cuando un payload tóxico llega.
- El usuario nunca ve un `pending_confirmation` con URL hacia metadata cloud.
- No se intenta crear el timesheet en Odoo.

Las tools (`prepare_summary`, `create_timesheet_entries`) están decoradas con
`@tool` de LangChain, así que las invocamos con `.invoke(...)` (el wrapper
de LangChain) para preservar la firma esperada.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.tools.project_tools import prepare_summary, create_timesheet_entries


def _runtime(employee_id: int = 1) -> SimpleNamespace:
    """Construye un objeto runtime mínimo compatible con la firma de la tool.
    Solo se accede a `runtime.context.employee_id`, así que un SimpleNamespace
    es suficiente y evita la validación Pydantic estricta de
    `langchain_core.tools.ToolRuntime`."""
    return SimpleNamespace(context=SimpleNamespace(employee_id=employee_id))


_MALICIOUS_PAYLOADS = [
    # Bypass exacto del pentest (IP decimal 32-bit).
    "http://2852039166/latest/meta-data/iam/security-credentials/railway",
    # AWS metadata clásico.
    "http://169.254.169.254/latest/",
    # Hex 32-bit.
    "http://0xa9fea9fe/latest/",
    # Octal por octeto.
    "http://0251.0376.0251.0376/latest/",
    # GCP metadata hostname.
    "http://metadata.google.internal/computeMetadata/v1/",
    # IPv6 loopback.
    "http://[::1]:8000/admin",
]


@pytest.mark.parametrize("description", _MALICIOUS_PAYLOADS)
def test_prepare_summary_rejects_internal_url_in_description(description):
    """`prepare_summary` debe rechazar el payload SIN tocar Odoo."""
    entries_json = json.dumps(
        [
            {
                "project_id": 86,
                "task_id": None,
                "hours": 1.0,
                "date_str": "2026-05-11",
                "description": description,
            }
        ]
    )

    # Si el filtro NO funciona, la tool intentaría abrir una conexión a Odoo:
    # patchamos `get_odoo_connection` para detectar ese leak y para evitar que
    # un fallo del filtro contamine el test con una llamada real.
    with patch(
        "agent.tools.project_tools.get_odoo_connection",
        side_effect=AssertionError("El filtro VT-12 dejó pasar el payload"),
    ):
        raw = prepare_summary.func(entries_json=entries_json)

    result = json.loads(raw)
    assert result["success"] is False
    assert result["error"] == "URL no permitida"
    assert "interno" in result["message"].lower()


@pytest.mark.parametrize("description", _MALICIOUS_PAYLOADS)
def test_create_timesheet_entries_rejects_internal_url_in_description(description):
    """Defensa profunda: si el LLM saltea `prepare_summary` y va directo a
    `create_timesheet_entries`, también debe rechazar el payload sin tocar
    Odoo y sin construir el `CargarHorasRequest`."""
    entries_json = json.dumps(
        [
            {
                "project_id": 86,
                "task_id": None,
                "hours": 1.0,
                "date_str": "2026-05-11",
                "description": description,
            }
        ]
    )

    with patch(
        "agent.tools.project_tools.get_odoo_connection",
        side_effect=AssertionError("El filtro VT-12 dejó pasar el payload"),
    ):
        raw = create_timesheet_entries.func(
            runtime=_runtime(employee_id=1),
            entries_json=entries_json,
        )

    result = json.loads(raw)
    assert result["success"] is False
    assert result["error"] == "URL no permitida"


def test_prepare_summary_rejects_only_the_offending_entry_in_a_batch():
    """Si una entrada del lote es tóxica, se rechaza todo el lote (no se
    crea ningún timesheet)."""
    entries_json = json.dumps(
        [
            {
                "project_id": 86,
                "task_id": None,
                "hours": 1.0,
                "date_str": "2026-05-11",
                "description": "Revisión de código",
            },
            {
                "project_id": 86,
                "task_id": None,
                "hours": 1.0,
                "date_str": "2026-05-12",
                "description": "http://2852039166/latest/",
            },
        ]
    )

    with patch(
        "agent.tools.project_tools.get_odoo_connection",
        side_effect=AssertionError("No deberíamos llegar a Odoo"),
    ):
        raw = prepare_summary.func(entries_json=entries_json)

    result = json.loads(raw)
    assert result["success"] is False
    assert result["error"] == "URL no permitida"
    # El mensaje debe identificar QUÉ entrada falló.
    assert "Entrada 2" in result["message"]
