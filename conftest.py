import os
import sys

import pytest

# Añadir el directorio raíz del proyecto al path de Python
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


@pytest.fixture(autouse=True)
def _clear_authz_caches():
    """Las cachés de autoridad son globales al proceso: se vacían entre tests
    para que un test no vea datos guardados por otro."""
    from app.team.application import team_access

    for cache in (
        team_access._USER_ID_CACHE,
        team_access._LED_PROJECTS_CACHE,
        team_access._APPROVERS_CACHE,
        team_access._COVERAGE_CACHE,
    ):
        cache.clear()
    yield 