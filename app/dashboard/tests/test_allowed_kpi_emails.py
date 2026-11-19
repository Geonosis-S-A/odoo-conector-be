from app.dashboard.api.routers import _parse_allowed_emails


def test_parse_acepta_coma_punto_y_coma_y_espacios():
    raw = "Ana@x.com, bob@x.com;carla@x.com  dani@x.com"
    assert _parse_allowed_emails(raw) == {
        "ana@x.com",
        "bob@x.com",
        "carla@x.com",
        "dani@x.com",
    }


def test_parse_vacio_no_permite_a_nadie():
    assert _parse_allowed_emails("") == set()
    assert _parse_allowed_emails(None) == set()


def test_una_subcadena_no_alcanza_para_pasar():
    allowed = _parse_allowed_emails("ana.perez@x.com")
    assert "ana" not in allowed
    assert "perez@x.com" not in allowed
    assert "ana.perez@x.com" in allowed
