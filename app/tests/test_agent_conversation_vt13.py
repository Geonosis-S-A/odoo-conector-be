"""VT-13: IDOR en DELETE /agent/conversation/{id} — thread acotado al user_id del JWT."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent.api import routers as agent_routers
from app.shared.security.dependencies import get_current_user


def _payload(uid: int = 10):
    return {
        "user_id": uid,
        "user_email": f"u{uid}@test.local",
        "user_name": "Test",
        "roles": [1],
        "exp": 9999999999,
    }


@pytest.fixture
def client_delete_ok():
    app = FastAPI()
    app.include_router(agent_routers.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: _payload(10)

    with patch.object(
        agent_routers,
        "delete_conversation",
        return_value={
            "success": True,
            "deleted_count": 2,
            "message": "ok",
        },
    ):
        yield TestClient(app)

    app.dependency_overrides.clear()


def test_delete_conversation_allowed_when_owner_matches(client_delete_ok):
    cid = "u10_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    r = client_delete_ok.delete(f"/api/v1/agent/conversation/{cid}")
    assert r.status_code == 200


def test_delete_conversation_forbidden_other_user(client_delete_ok):
    cid = "u99_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    r = client_delete_ok.delete(f"/api/v1/agent/conversation/{cid}")
    assert r.status_code == 403


def test_delete_conversation_bad_format(client_delete_ok):
    r = client_delete_ok.delete(
        "/api/v1/agent/conversation/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    assert r.status_code == 400


def test_parse_agent_thread_owner():
    from app.shared.security.agent_conversation_id import (
        parse_agent_thread_owner,
        thread_owned_by_user,
    )

    assert parse_agent_thread_owner("u42_xyz") == 42
    assert parse_agent_thread_owner("plain-uuid") is None
    assert thread_owned_by_user("u42_a", 42) is True
    assert thread_owned_by_user("u42_a", 7) is False
