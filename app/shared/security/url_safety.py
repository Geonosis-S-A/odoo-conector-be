"""Detección de URLs / IPs hacia recursos internos en texto libre.

Construido en respuesta a VT-12 (pentest 2026-04, GEO-1388). El reporte
demostró que el filtro del agente IA contra el metadata endpoint de AWS
(`http://169.254.169.254/...`) era a nivel LLM y se bypasseaba con la IP en
formato decimal (`http://2852039166/...`). Este módulo provee una validación
a nivel código, independiente del modelo, que detecta IPs internas en todas
las representaciones que la stack de red admite.

Cobertura:
- IPv4 dotted clásico: `169.254.169.254`.
- IPv4 dotted con octetos en hex u octal: `0xa9.0xfe.0xa9.0xfe`,
  `0251.0376.0251.0376`.
- IPv4 entero de 32 bits en decimal: `2852039166`.
- IPv4 entero de 32 bits en hex: `0xa9fea9fe`.
- IPv6 nativo (con o sin `[]`): `[::1]`, `fe80::1`.
- IPv6 con IPv4 mapped: `::ffff:169.254.169.254` / `::ffff:a9fe:a9fe`.
- Hostnames conocidos de metadata cloud (Google/Azure/AWS dual-stack).

Rangos considerados "internos":
- IPv4: `0/8`, `10/8`, `100.64/10` (CGNAT), `127/8`, `169.254/16` (link-local
  + AWS/GCP/Azure metadata), `172.16/12`, `192.168/16`, `198.18/15`
  (benchmarking), `224/4` (multicast), `240/4` (reserved).
- IPv6: `::1/128`, `fc00::/7` (ULA), `fe80::/10` (link-local).

Uso pretendido:
- `find_internal_url_targets(text)` retorna la lista de fragmentos
  problemáticos encontrados (no levanta excepción). Útil para validators y
  logging.
- `assert_no_internal_urls(text)` levanta `UnsafeUrlError` si encuentra algo.
- `safe_text_validator` está pensado como `@field_validator` de Pydantic para
  aplicar la regla sobre cualquier campo de texto libre.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

__all__ = [
    "UnsafeUrlError",
    "find_internal_url_targets",
    "assert_no_internal_urls",
    "safe_text_validator",
]


class UnsafeUrlError(ValueError):
    """Se intentó persistir un texto que contiene una URL hacia un recurso
    interno (link-local, RFC 1918, loopback, etc.).

    Hereda de `ValueError` para integrarse de forma natural con Pydantic, que
    convierte estas excepciones en `ValidationError`s estructurados.
    """

    def __init__(self, targets: list[str]):
        self.targets = targets
        preview = ", ".join(targets[:3])
        super().__init__(
            f"El texto contiene URL(s) hacia recursos internos no permitidos: {preview}"
        )


# ---------------------------------------------------------------------------
# Rangos prohibidos
# ---------------------------------------------------------------------------

_INTERNAL_NETS_V4: tuple[ipaddress.IPv4Network, ...] = (
    ipaddress.IPv4Network("0.0.0.0/8"),
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("100.64.0.0/10"),
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.0.0.0/24"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("198.18.0.0/15"),
    ipaddress.IPv4Network("224.0.0.0/4"),
    ipaddress.IPv4Network("240.0.0.0/4"),
)

_INTERNAL_NETS_V6: tuple[ipaddress.IPv6Network, ...] = (
    ipaddress.IPv6Network("::1/128"),
    ipaddress.IPv6Network("fc00::/7"),
    ipaddress.IPv6Network("fe80::/10"),
)

# Hostnames conocidos del endpoint de metadata de cada cloud provider.
# DNS rebinding / resolución directa al apuntar a 169.254.169.254.
_FORBIDDEN_HOSTNAMES: frozenset[str] = frozenset(
    {
        "metadata.google.internal",
        "metadata.goog",
        "metadata.azure.com",
        "metadata.azure.net",
        "instance-data",  # AWS alias interno
        "localhost",
    }
)


# ---------------------------------------------------------------------------
# Parseo de hosts en múltiples representaciones
# ---------------------------------------------------------------------------


def _parse_octet(part: str) -> int | None:
    """Parsea un octeto IPv4 aceptando decimal, hex (`0x..`) u octal (`0..`)."""
    if not part:
        return None
    lowered = part.lower()
    try:
        if lowered.startswith("0x"):
            return int(part, 16)
        # Octal "legacy" estilo inet_aton: cualquier número con leading zero
        # y dígitos válidos en base 8. "0" solo es 0 decimal.
        if len(part) > 1 and part[0] == "0" and all(c in "01234567" for c in part[1:]):
            return int(part, 8)
        return int(part)
    except ValueError:
        return None


def _try_parse_ipv4(host: str) -> ipaddress.IPv4Address | None:
    """Intenta interpretar `host` como IPv4 en cualquier formato que la stack
    de red podría aceptar (dotted multi-base + entero 32-bit).

    Soportamos las formas de `inet_aton(3)`:
    - `a.b.c.d` (clásica, base mixta por octeto)
    - `a.b.c`   (último valor toma 16 bits)
    - `a.b`     (último valor toma 24 bits)
    - `a`       (toma 32 bits)
    """
    if not host:
        return None

    parts = host.split(".")
    if not 1 <= len(parts) <= 4:
        return None

    nums: list[int] = []
    for part in parts:
        n = _parse_octet(part)
        if n is None or n < 0:
            return None
        nums.append(n)

    try:
        if len(nums) == 4:
            if any(n > 0xFF for n in nums):
                return None
            value = (nums[0] << 24) | (nums[1] << 16) | (nums[2] << 8) | nums[3]
        elif len(nums) == 3:
            if any(n > 0xFF for n in nums[:2]) or nums[2] > 0xFFFF:
                return None
            value = (nums[0] << 24) | (nums[1] << 16) | nums[2]
        elif len(nums) == 2:
            if nums[0] > 0xFF or nums[1] > 0xFFFFFF:
                return None
            value = (nums[0] << 24) | nums[1]
        else:
            if nums[0] > 0xFFFFFFFF:
                return None
            value = nums[0]
    except (TypeError, ValueError):
        return None

    if not 0 <= value <= 0xFFFFFFFF:
        return None
    return ipaddress.IPv4Address(value)


def _try_parse_ipv6(host: str) -> ipaddress.IPv6Address | None:
    """Parsea IPv6 (con o sin `[]`)."""
    candidate = host.strip("[]")
    if ":" not in candidate:
        return None
    try:
        return ipaddress.IPv6Address(candidate)
    except (ipaddress.AddressValueError, ValueError):
        return None


def _is_internal(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """¿La IP cae en alguno de los rangos vetados?"""
    if isinstance(ip, ipaddress.IPv6Address):
        # IPv4-mapped (::ffff:1.2.3.4) → analizar como IPv4 nativa.
        mapped = ip.ipv4_mapped
        if mapped is not None:
            return any(mapped in net for net in _INTERNAL_NETS_V4)
        return any(ip in net for net in _INTERNAL_NETS_V6)
    return any(ip in net for net in _INTERNAL_NETS_V4)


# ---------------------------------------------------------------------------
# Detección sobre texto libre
# ---------------------------------------------------------------------------

# URL completa con esquema. Permite cualquier esquema (no solo http) porque
# `file://`, `gopher://`, `dict://`, `ftp://`, `ldap://`, etc. también son
# vectores válidos de SSRF / data exfiltration.
_URL_SCHEME_RE = re.compile(
    r"""
    \b
    (?:[a-z][a-z0-9+\-.]*://)        # esquema://
    (?:[^\s/?#@'"<>]*@)?             # userinfo opcional (user:pass@)
    (
        \[[0-9a-fA-F:.]+\]           # IPv6 entre brackets
        |
        [^\s/?#:'"<>]+               # host (hasta separador URL)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# IPv4 dotted (con posibles octetos en hex/octal) sin requerir esquema.
_IPV4_DOTTED_RE = re.compile(
    r"""
    (?<![\w.])
    (?:
        0[xX][0-9a-fA-F]+    # hex
        |
        0[0-7]+              # octal con leading zero
        |
        \d+                  # decimal
    )
    (?:
        \.
        (?:0[xX][0-9a-fA-F]+|0[0-7]+|\d+)
    ){1,3}
    (?![\w.])
    """,
    re.VERBOSE,
)

# Entero suelto de >= 8 dígitos: candidato a IPv4 en formato decimal 32-bit.
# Filtro mínimo para evitar falsos positivos con números pequeños (ids, horas)
# pero atrapar la conversión decimal de cualquier IPv4 (>= 2^24 = 16777216).
_LARGE_INT_RE = re.compile(r"(?<![\w.])(\d{8,10})(?![\w.])")

# IPv4 en hex "plano" tipo 0xa9fea9fe.
_HEX_INT_RE = re.compile(r"(?<![\w])0[xX]([0-9a-fA-F]{1,8})(?![\w])")

# IPv6 fuera de URL (puede estar pelado en texto). Pedimos al menos dos `::`
# o varios grupos hex separados por `:` para reducir falsos positivos.
_IPV6_RE = re.compile(
    r"(?<![\w:])(\[[0-9a-fA-F:.]+\]|::1\b|[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){2,7})(?![\w:])"
)


def _extract_host(url_match: str) -> str:
    """Extrae el host de una URL ya capturada (sin puerto, sin path, sin
    userinfo)."""
    # Cortar en separadores que no pertenecen al host.
    for sep in ("/", "?", "#"):
        if sep in url_match:
            url_match = url_match.split(sep, 1)[0]
    # Quitar puerto cuando no es IPv6 entre brackets.
    if not url_match.startswith("["):
        if url_match.count(":") == 1:
            url_match = url_match.split(":", 1)[0]
    return url_match


def _host_is_internal(host: str) -> bool:
    """¿Este host (string) resuelve a un recurso interno?"""
    if not host:
        return False
    lowered = host.lower().rstrip(".")
    if lowered in _FORBIDDEN_HOSTNAMES:
        return True
    ipv4 = _try_parse_ipv4(host)
    if ipv4 is not None and _is_internal(ipv4):
        return True
    ipv6 = _try_parse_ipv6(host)
    if ipv6 is not None and _is_internal(ipv6):
        return True
    return False


@dataclass(frozen=True)
class _Finding:
    """Representa un fragmento del texto que coincide con un target interno."""

    raw: str
    reason: str


def _scan(text: str) -> list[_Finding]:
    findings: list[_Finding] = []

    # 1) URLs con esquema explícito.
    for match in _URL_SCHEME_RE.finditer(text):
        raw = match.group(0)
        host = _extract_host(match.group(1))
        if _host_is_internal(host):
            findings.append(_Finding(raw=raw, reason=f"url->host:{host}"))

    # 2) IPv4 dotted sin esquema (incluye hex/octal por octeto).
    for match in _IPV4_DOTTED_RE.finditer(text):
        host = match.group(0)
        if _host_is_internal(host):
            findings.append(_Finding(raw=host, reason="ipv4-dotted"))

    # 3) Entero grande (potencial IPv4 32-bit decimal).
    for match in _LARGE_INT_RE.finditer(text):
        host = match.group(1)
        if _host_is_internal(host):
            findings.append(_Finding(raw=host, reason="ipv4-decimal-int"))

    # 4) Entero grande en hex (0xa9fea9fe).
    for match in _HEX_INT_RE.finditer(text):
        host = "0x" + match.group(1)
        if _host_is_internal(host):
            findings.append(_Finding(raw=host, reason="ipv4-hex-int"))

    # 5) IPv6 pelado.
    for match in _IPV6_RE.finditer(text):
        candidate = match.group(1)
        if _host_is_internal(candidate):
            findings.append(_Finding(raw=candidate, reason="ipv6"))

    # 6) Hostnames de metadata cloud literales.
    lowered = text.lower()
    for hostname in _FORBIDDEN_HOSTNAMES:
        if hostname in lowered:
            findings.append(_Finding(raw=hostname, reason="metadata-hostname"))

    return findings


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def find_internal_url_targets(text: str | None) -> list[str]:
    """Devuelve los fragmentos del texto que apuntan a un recurso interno.

    Lista vacía cuando el texto es seguro (o vacío/None). El orden de la lista
    es el de aparición en el texto; los duplicados se conservan (puede ser
    útil para logging forense).
    """
    if not text:
        return []
    return [f.raw for f in _scan(text)]


def assert_no_internal_urls(text: str | None) -> None:
    """Versión que levanta. Pensada para usarse desde validators de Pydantic
    o desde tools del agente donde queremos abortar el flujo."""
    targets = find_internal_url_targets(text)
    if targets:
        raise UnsafeUrlError(targets)


def safe_text_validator(value: str | None) -> str | None:
    """Adaptador para `@field_validator` de Pydantic.

    Se mantiene el valor original (no se sanitiza ni se trunca) si pasa la
    validación; si no, se levanta `UnsafeUrlError`. Devolver el texto sin
    modificar mantiene la compatibilidad con clientes legítimos.
    """
    if value is None:
        return None
    assert_no_internal_urls(value)
    return value
