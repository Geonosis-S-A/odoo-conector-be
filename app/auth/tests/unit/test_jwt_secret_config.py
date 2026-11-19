"""JWT_SECRET_KEY: obligatoria en STAGING/PROD, con clave de desarrollo solo en local."""

import pytest

from app.auth.infra.auth_service import _load_jwt_secret


@pytest.mark.parametrize("env", ["STAGING", "PROD", "prod"])
def test_falta_la_clave_en_staging_o_prod_falla(monkeypatch, env):
    monkeypatch.setenv("ENV", env)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        _load_jwt_secret()


@pytest.mark.parametrize("env", ["STAGING", "PROD"])
def test_clave_por_defecto_en_staging_o_prod_falla(monkeypatch, env):
    monkeypatch.setenv("ENV", env)
    monkeypatch.setenv("JWT_SECRET_KEY", "default_secret_key")
    with pytest.raises(RuntimeError):
        _load_jwt_secret()


@pytest.mark.parametrize("env", ["STAGING", "PROD"])
def test_clave_real_en_staging_o_prod_se_usa(monkeypatch, env):
    monkeypatch.setenv("ENV", env)
    monkeypatch.setenv("JWT_SECRET_KEY", "una-clave-larga-y-aleatoria")
    assert _load_jwt_secret() == "una-clave-larga-y-aleatoria"


def test_en_local_sin_clave_usa_la_de_desarrollo(monkeypatch):
    monkeypatch.setenv("ENV", "LOCAL")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    assert _load_jwt_secret()
