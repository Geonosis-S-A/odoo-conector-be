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


class TestRequestLento:
    def test_loguea_un_request_que_supera_el_umbral(self, monkeypatch, caplog):
        monkeypatch.setattr("app.shared.utils.server_timing.SLOW_REQUEST_MS", 10)

        with caplog.at_level("INFO", logger="server_timing"):
            _app_con_endpoint_lento().get("/lento?project_id=7")

        mensajes = [r.getMessage() for r in caplog.records]
        assert any(
            m.startswith("SLOW REQUEST GET /lento?project_id=7 status=200 app=")
            for m in mensajes
        )

    def test_no_loguea_un_request_rapido(self, caplog):
        with caplog.at_level("INFO", logger="server_timing"):
            _app_con_endpoint_lento().get("/lento")  # 50 ms << 1000 ms

        assert not any("SLOW REQUEST" in r.getMessage() for r in caplog.records)

    def test_no_loguea_headers_ni_tokens(self, monkeypatch, caplog):
        monkeypatch.setattr("app.shared.utils.server_timing.SLOW_REQUEST_MS", 10)

        with caplog.at_level("INFO", logger="server_timing"):
            _app_con_endpoint_lento().get(
                "/lento", headers={"Authorization": "Bearer super-secreto"}
            )

        assert "super-secreto" not in caplog.text


class TestTiempoPrevioAlCasoDeUso:
    def _app(self) -> TestClient:
        from fastapi import Depends

        from app.shared.utils.step_timer import StepTimer

        app = FastAPI()
        app.add_middleware(ServerTimingMiddleware)

        def dependencia_lenta():
            time.sleep(0.06)

        @app.get("/caso")
        def caso(_=Depends(dependencia_lenta)):
            timer = StepTimer("prueba")
            timer.log()
            return {"ok": True}

        return TestClient(app)

    def test_pre_refleja_lo_que_tardo_antes_del_caso_de_uso(self, caplog):
        with caplog.at_level("INFO", logger="step_timer"):
            self._app().get("/caso")

        linea = next(r.getMessage() for r in caplog.records if "TIMING prueba" in r.getMessage())
        pre_ms = int(re.search(r"pre=(\d+)ms", linea).group(1))
        assert pre_ms >= 55  # la dependencia duerme 60 ms antes del caso de uso

    def test_fuera_de_un_request_no_hay_pre(self, caplog):
        from app.shared.utils.step_timer import StepTimer

        with caplog.at_level("INFO", logger="step_timer"):
            StepTimer("suelto").log()

        linea = next(r.getMessage() for r in caplog.records if "TIMING suelto" in r.getMessage())
        assert "pre=" not in linea
