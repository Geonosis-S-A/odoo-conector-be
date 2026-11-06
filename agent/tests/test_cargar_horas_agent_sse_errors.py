"""POST /agent/cargar-horas-agent: si el asistente falla, el error llega al cliente.

Antes, una falla antes del primer mensaje (por ejemplo una clave de OpenAI inválida)
dejaba la conexión muda durante 5 minutos, hasta que el proxy la cortaba. Ahora el
cliente recibe un aviso enseguida, sin los detalles internos del error.
"""

import json
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.security.dependencies import get_current_user
from agent.api import routers as agent_routers

SECRET_DETAIL = "Incorrect API key provided: sk-proj-SECRETO-1234"


def _events(body: str) -> list[dict]:
    return [
        json.loads(line[len("data: "):])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def _post(monkeypatch, fake_service):
    monkeypatch.setattr(agent_routers, "run_agent_service", fake_service)
    app = FastAPI()
    app.include_router(agent_routers.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 7,
        "user_email": "x@example.com",
        "user_name": "X",
        "roles": [],
    }
    client = TestClient(app, raise_server_exceptions=False)
    result = {}

    def call():
        result["resp"] = client.post(
            "/api/v1/agent/cargar-horas-agent",
            json={"conversation_id": "c1", "prompt": "cargá 8 horas"},
        )

    thread = threading.Thread(target=call, daemon=True)
    thread.start()
    thread.join(10)
    assert not thread.is_alive(), "la respuesta quedó colgada (no terminó en 10 s)"
    return result["resp"]


def test_falla_antes_del_primer_mensaje_avisa_y_termina(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError(SECRET_DETAIL)

    resp = _post(monkeypatch, broken)

    events = _events(resp.text)
    assert [e["type"] for e in events] == ["error", "done"]
    assert events[0]["content"] == agent_routers.ASSISTANT_UNAVAILABLE_MESSAGE


def test_el_detalle_del_error_no_llega_al_cliente(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError(SECRET_DETAIL)

    resp = _post(monkeypatch, broken)

    assert "sk-proj" not in resp.text
    assert "SECRETO" not in resp.text


def test_falla_a_mitad_de_la_respuesta_conserva_lo_enviado(monkeypatch):
    def half_way(*args, **kwargs):
        yield {"type": "text", "content": "Hola"}
        raise RuntimeError(SECRET_DETAIL)

    resp = _post(monkeypatch, half_way)

    events = _events(resp.text)
    assert [e["type"] for e in events] == ["text", "error", "done"]
    assert events[0]["content"] == "Hola"
    assert "sk-proj" not in resp.text


def test_respuesta_normal_no_cambia(monkeypatch):
    def fine(*args, **kwargs):
        yield {"type": "text", "content": "Listo"}

    resp = _post(monkeypatch, fine)

    events = _events(resp.text)
    assert [e["type"] for e in events] == ["text", "done"]
