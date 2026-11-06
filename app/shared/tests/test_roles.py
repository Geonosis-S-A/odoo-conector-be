import pytest

from app.shared.security.roles import load_roles_enum


@pytest.mark.parametrize(
    "env, approver",
    [
        ("LOCAL", 31),
        ("STAGING", 80),
        # El front de producción usa el mismo grupo que staging (80)
        ("PROD", 80),
        ("prod", 80),
    ],
)
def test_approver_role_id_por_entorno(monkeypatch, env, approver):
    monkeypatch.setenv("ENV", env)

    assert int(load_roles_enum().approver) == approver
