"""Smoke test manual de la API de equipos (Opción 2) contra un entorno real.

Ejercita el flujo completo: el líder ve su equipo (jerarquía Odoo en vivo),
asigna/quita permisos, y se comprueba el efecto en /timesheet.

Uso:
    python scripts/smoke_teams.py \
        --base-url https://<staging>/api/v1 \
        --leader-email lider@empresa.com --leader-pass '...' \
        --member-email miembro@empresa.com --member-pass '...' \
        [--date-from 2026-09-01 --date-to 2026-09-30] \
        [--validate-ids 123,124]   # IDs de líneas NO validadas de gente del equipo

No escribe nada irreversible salvo:
  - crea/borra la fila de permiso del miembro (la deja en 'none' al final)
  - si pasás --validate-ids, valida esas líneas en Odoo (eso NO se revierte)
"""
from __future__ import annotations

import argparse
import sys

import httpx

OK = "\033[92m✓\033[0m"
BAD = "\033[91m✗\033[0m"


def login(client: httpx.Client, base_url: str, email: str, password: str) -> dict:
    r = client.post(
        f"{base_url}/auth/login", json={"email": email, "password": password}
    )
    r.raise_for_status()
    body = r.json()
    return {
        "token": body["access_token"],
        "user_id": body["user"]["user_id"],
        "roles": body["user"].get("roles", []),
    }


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def check(label: str, got: int, expected: int) -> bool:
    ok = got == expected
    print(f"  {OK if ok else BAD} {label}: HTTP {got} (esperado {expected})")
    return ok


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True, help="ej: https://staging.../api/v1")
    p.add_argument("--leader-email", required=True)
    p.add_argument("--leader-pass", required=True)
    p.add_argument("--member-email", required=True)
    p.add_argument("--member-pass", required=True)
    p.add_argument("--date-from", default="2026-09-01")
    p.add_argument("--date-to", default="2026-09-30")
    p.add_argument(
        "--validate-ids",
        default="",
        help="CSV de timesheetline_ids NO validados de gente del equipo",
    )
    args = p.parse_args()

    base = args.base_url.rstrip("/")
    results: list[bool] = []

    with httpx.Client(timeout=60) as c:
        # --- auth ---
        leader = login(c, base, args.leader_email, args.leader_pass)
        member = login(c, base, args.member_email, args.member_pass)
        print(f"\nLíder  user_id={leader['user_id']} roles={leader['roles']}")
        print(f"Miembro user_id={member['user_id']} roles={member['roles']}\n")

        # --- 1. el líder ve su equipo (jerarquía Odoo) ---
        r = c.get(f"{base}/teams/mine", headers=h(leader["token"]))
        results.append(check("GET /teams/mine (líder)", r.status_code, 200))
        if r.status_code != 200:
            print("  El usuario --leader-* no lidera equipo en Odoo. Abortando.")
            return 1
        team = r.json()
        members = team["members"]
        print(f"  equipo Odoo del líder {team['leader_employee_odoo_id']}: "
              f"{[(m['employee_odoo_id'], m['name'], m['level']) for m in members]}")

        member_ids = {m["employee_odoo_id"] for m in members}
        if member["user_id"] not in member_ids:
            print(f"  {BAD} --member-* (id {member['user_id']}) NO está en el "
                  f"equipo Odoo del líder. Elegí otro miembro.")
            return 1
        print(f"  {OK} --member-* está en el equipo del líder")

        target = member["user_id"]

        # --- 2. asignar 'validate' ---
        r = c.put(
            f"{base}/teams/mine/members/{target}",
            headers=h(leader["token"]),
            json={"level": "validate"},
        )
        results.append(check("PUT .../members (level=validate)", r.status_code, 200))
        if r.status_code == 200:
            print(f"  -> {r.json()}")

        # --- 3. asignar a alguien fuera del equipo -> 400 ---
        bogus = max(member_ids) + 999999
        r = c.put(
            f"{base}/teams/mine/members/{bogus}",
            headers=h(leader["token"]),
            json={"level": "view"},
        )
        results.append(check("PUT .../members (fuera del equipo)", r.status_code, 400))

        # --- 4. el miembro (con validate) ahora ve el equipo ---
        r = c.get(
            f"{base}/timesheet/",
            headers=h(member["token"]),
            params={"team": "true", "date_from": args.date_from,
                    "date_to": args.date_to},
        )
        results.append(check("GET /timesheet/?team=true (miembro validate)",
                             r.status_code, 200))
        if r.status_code == 200:
            print(f"  -> {len(r.json())} líneas visibles")

        # --- 5. bajar a 'view': ya NO puede validar ---
        c.put(f"{base}/teams/mine/members/{target}", headers=h(leader["token"]),
              json={"level": "view"})
        r = c.post(
            f"{base}/timesheet/validate",
            headers=h(member["token"]),
            json={"approver_mail": args.member_email, "timesheetline_ids": [1]},
        )
        results.append(check("POST /timesheet/validate (miembro solo 'view')",
                             r.status_code, 403))

        # --- 6. sin permiso: no ve el equipo ---
        c.put(f"{base}/teams/mine/members/{target}", headers=h(leader["token"]),
              json={"level": "none"})
        r = c.get(
            f"{base}/timesheet/",
            headers=h(member["token"]),
            params={"team": "true", "date_from": args.date_from,
                    "date_to": args.date_to},
        )
        results.append(check("GET /timesheet/?team=true (miembro sin permiso)",
                             r.status_code, 403))

        # --- 7. (opcional) validación real con 'validate' ---
        ids = [int(x) for x in args.validate_ids.split(",") if x.strip()]
        if ids:
            c.put(f"{base}/teams/mine/members/{target}",
                  headers=h(leader["token"]), json={"level": "validate"})
            r = c.post(
                f"{base}/timesheet/validate",
                headers=h(member["token"]),
                json={"approver_mail": args.member_email,
                      "timesheetline_ids": ids},
            )
            results.append(check(f"POST /timesheet/validate ids={ids}",
                                 r.status_code, 200))
            print(f"  -> {r.text[:300]}")
            print("  Revisá en Odoo que x_validated_by de esas líneas = "
                  f"empleado {member['user_id']} (el miembro que validó)")
            c.put(f"{base}/teams/mine/members/{target}",
                  headers=h(leader["token"]), json={"level": "none"})
        else:
            print("  (saltado: pasá --validate-ids para probar validación real)")

    print()
    passed = sum(results)
    total = len(results)
    print(f"{OK if passed == total else BAD} {passed}/{total} checks OK")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
