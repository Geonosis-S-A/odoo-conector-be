"""VT-09: identidad del reporte de soporte sólo desde JWT, no desde el body."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.email.api.dependencies import get_common_email_service
from app.email.api.routes import router
from app.shared.security.dependencies import get_current_user


class StubEmailService:
    def __init__(self):
        self.calls = []

    async def send_support_mail(
        self, user_name, user_email, subject, body, reported_at
    ):
        self.calls.append(
            {
                "user_name": user_name,
                "user_email": user_email,
                "subject": subject,
                "body": body,
                "reported_at": reported_at,
            }
        )


@pytest.fixture
def client_and_stub():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    stub = StubEmailService()

    async def user_override():
        return {
            "user_id": 7,
            "user_email": "jwt.user@geonosis.test",
            "user_name": "Nombre JWT",
            "roles": [1],
            "exp": 9999999999,
        }

    app.dependency_overrides[get_common_email_service] = lambda: stub
    app.dependency_overrides[get_current_user] = user_override
    tc = TestClient(app)
    yield tc, stub
    app.dependency_overrides.clear()


def test_support_mail_identity_from_jwt_not_body(client_and_stub):
    client, stub = client_and_stub
    r = client.post(
        "/api/v1/email/support-mail",
        json={"subject": "Fallo UI", "body": "No carga el listado"},
    )
    assert r.status_code == 200
    assert len(stub.calls) == 1
    c = stub.calls[0]
    assert c["user_name"] == "Nombre JWT"
    assert c["user_email"] == "jwt.user@geonosis.test"
    assert c["subject"] == "Fallo UI"
    assert c["body"] == "No carga el listado"


def test_support_mail_rejects_spoof_extra_fields(client_and_stub):
    client, stub = client_and_stub
    r = client.post(
        "/api/v1/email/support-mail",
        json={
            "subject": "x",
            "body": "y",
            "user_name": "CEO Falso",
            "date": "2020-01-01T00:00:00Z",
        },
    )
    assert r.status_code == 422
    assert stub.calls == []
