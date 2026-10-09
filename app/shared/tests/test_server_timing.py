import re
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import allowed_origins, app as real_app
from app.shared.utils.server_timing import ServerTimingMiddleware

SERVER_TIMING = re.compile(r"^app;dur=(\d+)$")


def _app_con_endpoint_lento() -> TestClient:
    app = FastAPI()
    app.add_middleware(ServerTimingMiddleware)

    @app.get("/lento")
    def lento():
        time.sleep(0.05)
        return {"ok": True}

    return TestClient(app)


class TestServerTiming:
    def test_agrega_el_encabezado_con_el_formato_esperado(self):
        response = _app_con_endpoint_lento().get("/lento")

        assert response.status_code == 200
        assert SERVER_TIMING.match(response.headers["server-timing"])

    def test_mide_el_tiempo_real_del_endpoint(self):
        response = _app_con_endpoint_lento().get("/lento")

        duration_ms = int(SERVER_TIMING.match(response.headers["server-timing"]).group(1))
        assert duration_ms >= 45  # el endpoint duerme 50 ms

    def test_no_altera_el_cuerpo_ni_el_status(self):
        response = _app_con_endpoint_lento().get("/lento")

        assert response.json() == {"ok": True}


class TestPreflightCors:
    def _preflight(self):
        return TestClient(real_app).options(
            "/api/v1/timesheet/",
            headers={
                "Origin": allowed_origins[0],
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )

    def test_el_navegador_puede_cachear_el_preflight_dos_horas(self):
        response = self._preflight()

        assert response.status_code == 200
        assert response.headers["access-control-max-age"] == "7200"

    def test_el_preflight_tambien_trae_server_timing(self):
        assert SERVER_TIMING.match(self._preflight().headers["server-timing"])

    def test_un_origen_no_permitido_sigue_sin_autorizarse(self):
        response = TestClient(real_app).options(
            "/api/v1/timesheet/",
            headers={
                "Origin": "https://sitio-ajeno.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers
