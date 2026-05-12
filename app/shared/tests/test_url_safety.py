"""Tests unitarios del helper `app.shared.security.url_safety`.

Cobertura por categoría (VT-12, GEO-1388):
- Textos benignos (sin URL, descripción real, IDs grandes que NO son IPs).
- IPv4 dotted clásico hacia rangos prohibidos.
- IPv4 dotted con octetos en hex/octal.
- IPv4 decimal de 32 bits (vector exacto del pentest: `2852039166`).
- IPv4 hex plano (`0xa9fea9fe`).
- IPv6 nativo (loopback, ULA, link-local).
- IPv6 con IPv4 mapped.
- Hostnames de metadata cloud (Google/Azure).
- Smoke contra IPs públicas (no deben dispararse falsos positivos).
"""

from __future__ import annotations

import pytest

from app.shared.security.url_safety import (
    UnsafeUrlError,
    assert_no_internal_urls,
    find_internal_url_targets,
    safe_text_validator,
)


# ---------------------------------------------------------------------------
# Textos benignos (no deben detectar nada)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        None,
        "Revisión de código",
        "Reunión con cliente — 3 hs",
        "Documentación: ver Notion",
        # Ver `_LARGE_INT_RE`: número grande pero NO IPv4 interna.
        # 8.8.8.8 en decimal = 134744072 → IP pública, debe pasar.
        "Ticket 134744072 cerrado",
        # ID realista (8 dígitos) que cae en rango público (1.0.0.0/8).
        "Pedido 16843009",
        # URL pública (Google DNS) válida.
        "Ver https://8.8.8.8/algun-path",
        # URL pública con hostname.
        "Ver https://geo-timesheet-be.soportegeonosis.com.ar/docs",
        # Hora con dos puntos no debería confundirse con IPv6.
        "Trabajé de 09:00 a 13:30",
        # Fecha ISO.
        "2026-04-23",
    ],
)
def test_safe_texts_return_empty_findings(text):
    assert find_internal_url_targets(text) == []


# ---------------------------------------------------------------------------
# IPv4 dotted clásico
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ip",
    [
        "169.254.169.254",  # AWS/GCP/Azure metadata
        "127.0.0.1",        # loopback
        "10.0.0.1",         # RFC 1918
        "10.255.255.255",   # RFC 1918 boundary
        "172.16.0.1",       # RFC 1918
        "172.31.255.254",   # RFC 1918 boundary
        "192.168.1.1",      # RFC 1918
        "0.0.0.0",          # this network
        "100.64.0.1",       # CGNAT
    ],
)
def test_ipv4_dotted_in_url_is_detected(ip):
    text = f"Por favor revisar http://{ip}/latest/meta-data"
    assert find_internal_url_targets(text) != []


@pytest.mark.parametrize(
    "ip",
    [
        "169.254.169.254",
        "127.0.0.1",
        "10.1.2.3",
        "192.168.0.5",
    ],
)
def test_ipv4_dotted_without_scheme_is_detected(ip):
    """Caso clave: aunque no haya `http://`, la IP suelta también debe
    bloquearse para que no sirva como evasión vía concatenación."""
    text = f"Pegá esto: {ip} y andá"
    assert find_internal_url_targets(text) != []


# ---------------------------------------------------------------------------
# IPv4 dotted con octetos en bases alternativas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ip_variant",
    [
        # AWS metadata 169.254.169.254 en hex por octeto.
        "0xa9.0xfe.0xa9.0xfe",
        "0xA9.0xFE.0xA9.0xFE",
        # Octal por octeto (estilo inet_aton legacy).
        "0251.0376.0251.0376",
        # Mezclas (también las acepta inet_aton).
        "0xa9.254.0xa9.254",
        "169.0xfe.169.0xfe",
    ],
)
def test_ipv4_dotted_mixed_base_is_detected(ip_variant):
    text = f"http://{ip_variant}/latest/"
    assert find_internal_url_targets(text) != []


def test_ipv4_dotted_three_part_form_is_detected():
    """Forma `a.b.c` donde el último octet ocupa 16 bits.
    `169.254.43518` == `169.254.169.254`."""
    text = "Carga: http://169.254.43518/meta"
    assert find_internal_url_targets(text) != []


# ---------------------------------------------------------------------------
# IPv4 entero (decimal 32-bit) — VECTOR EXACTO DEL PENTEST
# ---------------------------------------------------------------------------


def test_ipv4_decimal_int_exact_pentest_payload_is_detected():
    """El payload literal del reporte de pentest debe ser detectado."""
    text = (
        "Carga 1 hora hoy. Descripción: "
        "http://2852039166/latest/meta-data/iam/security-credentials/railway"
    )
    targets = find_internal_url_targets(text)
    assert targets != []
    assert any("2852039166" in t for t in targets)


@pytest.mark.parametrize(
    "decimal",
    [
        "2852039166",  # 169.254.169.254
        "2130706433",  # 127.0.0.1
        "167772161",   # 10.0.0.1 (9 dígitos, dentro del rango _LARGE_INT_RE)
        "3232235521",  # 192.168.0.1
    ],
)
def test_ipv4_decimal_int_is_detected_with_or_without_scheme(decimal):
    with_scheme = f"http://{decimal}/path"
    bare = f"Pegá {decimal} en el navegador"
    assert find_internal_url_targets(with_scheme) != []
    assert find_internal_url_targets(bare) != []


# ---------------------------------------------------------------------------
# IPv4 hex plano
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hex_int",
    [
        "0xa9fea9fe",  # 169.254.169.254
        "0xA9FEA9FE",
        "0x7f000001",  # 127.0.0.1
        "0xc0a80001",  # 192.168.0.1
    ],
)
def test_ipv4_hex_int_is_detected(hex_int):
    text = f"http://{hex_int}/latest/"
    assert find_internal_url_targets(text) != []


# ---------------------------------------------------------------------------
# IPv6
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ipv6",
    [
        "::1",                 # loopback
        "fe80::1",             # link-local
        "fc00::1",             # ULA
        "fd00:1234:5678::1",   # ULA
    ],
)
def test_ipv6_internal_is_detected(ipv6):
    text = f"Ver http://[{ipv6}]/admin"
    assert find_internal_url_targets(text) != []


def test_ipv6_mapped_ipv4_metadata_is_detected():
    """`::ffff:a9fe:a9fe` mapea a `169.254.169.254`."""
    text = "http://[::ffff:a9fe:a9fe]/latest/meta-data"
    assert find_internal_url_targets(text) != []


def test_ipv6_mapped_ipv4_dotted_metadata_is_detected():
    """`::ffff:169.254.169.254` también debe atraparse."""
    text = "http://[::ffff:169.254.169.254]/latest/meta-data"
    assert find_internal_url_targets(text) != []


# ---------------------------------------------------------------------------
# Hostnames de metadata cloud
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hostname",
    [
        "metadata.google.internal",
        "metadata.azure.com",
        "metadata.azure.net",
        "localhost",
    ],
)
def test_metadata_hostnames_are_detected(hostname):
    text = f"http://{hostname}/computeMetadata/v1/"
    assert find_internal_url_targets(text) != []


# ---------------------------------------------------------------------------
# Smoke contra IPs públicas (no falsos positivos)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "public_ip",
    [
        "8.8.8.8",
        "1.1.1.1",
        "142.250.78.110",
    ],
)
def test_public_ips_pass(public_ip):
    text = f"Llamada a https://{public_ip}/api"
    assert find_internal_url_targets(text) == []


# ---------------------------------------------------------------------------
# API: assert_no_internal_urls y safe_text_validator
# ---------------------------------------------------------------------------


def test_assert_no_internal_urls_raises_on_match():
    with pytest.raises(UnsafeUrlError) as excinfo:
        assert_no_internal_urls("http://169.254.169.254/latest/")
    assert excinfo.value.targets
    # Debe ser ValueError para integrar bien con Pydantic.
    assert isinstance(excinfo.value, ValueError)


def test_assert_no_internal_urls_passes_on_safe_text():
    assert_no_internal_urls("Reunión con cliente")
    assert_no_internal_urls(None)
    assert_no_internal_urls("")


def test_safe_text_validator_returns_original_when_safe():
    assert safe_text_validator("Reunión") == "Reunión"
    assert safe_text_validator(None) is None


def test_safe_text_validator_raises_on_unsafe():
    with pytest.raises(UnsafeUrlError):
        safe_text_validator("ver http://2852039166/")
