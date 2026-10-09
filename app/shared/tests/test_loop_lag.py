import asyncio
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.utils.loop_lag import monitor_event_loop_lag
from app.shared.utils import server_timing
from app.shared.utils.server_timing import ServerTimingMiddleware, inflight_requests


async def _con_monitor(bloqueo_s: float, **kwargs) -> None:
    monitor = asyncio.create_task(monitor_event_loop_lag(**kwargs))
    await asyncio.sleep(0.05)  # deja que el monitor arranque
    time.sleep(bloqueo_s)  # código bloqueante ejecutándose en el event loop
    await asyncio.sleep(0.2)  # el monitor despierta y mide el atraso
    monitor.cancel()


class TestMonitorDeAtraso:
    def test_avisa_cuando_el_event_loop_se_bloquea(self, caplog):
        with caplog.at_level("INFO", logger="loop_lag"):
            asyncio.run(_con_monitor(0.4, interval=0.05, threshold=0.1))

        assert any("EVENT LOOP LAG" in r.getMessage() for r in caplog.records)

    def test_no_avisa_si_el_loop_responde(self, caplog):
        with caplog.at_level("INFO", logger="loop_lag"):
            asyncio.run(_con_monitor(0.0, interval=0.05, threshold=0.1))

        assert not any("EVENT LOOP LAG" in r.getMessage() for r in caplog.records)

    def test_el_aviso_trae_requests_en_vuelo_y_threadpool(self, caplog):
        with caplog.at_level("INFO", logger="loop_lag"):
            asyncio.run(_con_monitor(0.4, interval=0.05, threshold=0.1))

        linea = next(r.getMessage() for r in caplog.records if "EVENT LOOP LAG" in r.getMessage())
        assert "inflight=" in linea and "threadpool=" in linea


class TestRequestsEnVuelo:
    def _client(self) -> TestClient:
        app = FastAPI()
        app.add_middleware(ServerTimingMiddleware)

        @app.get("/lento")
        def lento():
            time.sleep(0.03)
            return {"en_vuelo": inflight_requests()}

        return TestClient(app)

    def test_cuenta_el_request_actual_y_vuelve_a_cero(self):
        client = self._client()

        assert client.get("/lento").json() == {"en_vuelo": 1}
        assert inflight_requests() == 0

    def test_se_decrementa_aunque_el_endpoint_falle(self):
        app = FastAPI()
        app.add_middleware(ServerTimingMiddleware)

        @app.get("/roto")
        def roto():
            raise RuntimeError("falla")

        TestClient(app, raise_server_exceptions=False).get("/roto")

        assert inflight_requests() == 0

    def test_el_log_de_lentos_trae_inflight_y_threadpool(self, monkeypatch, caplog):
        monkeypatch.setattr(server_timing, "SLOW_REQUEST_MS", 10)

        with caplog.at_level("INFO", logger="server_timing"):
            self._client().get("/lento")

        linea = next(r.getMessage() for r in caplog.records if "SLOW REQUEST" in r.getMessage())
        assert "inflight=1" in linea and "threadpool=" in linea
