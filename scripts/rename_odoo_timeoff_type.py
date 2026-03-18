#!/usr/bin/env python3
"""
Script para renombrar un tipo de licencia en Odoo.

Permite actualizar el valor base del campo `name` en `hr.leave.type`
y opcionalmente sincronizar una traduccion puntual.

Ejemplos:
    uv run python scripts/rename_odoo_timeoff_type.py --id 6 --new-name "Licencia por Vacaciones"
    uv run python scripts/rename_odoo_timeoff_type.py --id 6 --new-name "Licencia por Vacaciones" --translation-lang es_AR --sync-translation
    uv run python scripts/rename_odoo_timeoff_type.py --current-name "Licencia por Vacaciones (SI)" --lookup-lang en_US --new-name "Licencia por Vacaciones"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.shared.infra.external.odoo.odoo_client import OdooClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Renombra un tipo de licencia en Odoo (modelo hr.leave.type)."
    )
    parser.add_argument(
        "--id",
        type=int,
        help="ID del tipo de licencia en Odoo.",
    )
    parser.add_argument(
        "--current-name",
        help="Nombre actual para buscar el tipo de licencia.",
    )
    parser.add_argument(
        "--lookup-lang",
        default="en_US",
        help="Idioma usado para buscar por nombre actual. Default: en_US",
    )
    parser.add_argument(
        "--new-name",
        required=True,
        help="Nuevo nombre a asignar.",
    )
    parser.add_argument(
        "--base-lang",
        default="en_US",
        help="Idioma base en el que se escribira el valor fuente. Default: en_US",
    )
    parser.add_argument(
        "--translation-lang",
        default="es_AR",
        help="Idioma de traduccion a sincronizar si se usa --sync-translation. Default: es_AR",
    )
    parser.add_argument(
        "--sync-translation",
        action="store_true",
        help="Tambien actualiza una traduccion puntual con el mismo nombre.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No escribe cambios; solo muestra lo que haria.",
    )
    return parser.parse_args()


def get_connection() -> dict[str, Any]:
    client = OdooClient()
    return client.get_connection()


def search_leave_type_id(
    connection: dict[str, Any],
    current_name: str,
    lookup_lang: str,
) -> int:
    result = connection["models"].execute_kw(
        connection["ODOO_DB"],
        connection["uid"],
        connection["ODOO_PASSWORD"],
        "hr.leave.type",
        "search_read",
        [[["name", "=", current_name]]],
        {
            "fields": ["id", "name"],
            "limit": 2,
            "context": {"lang": lookup_lang},
        },
    )

    if not result:
        raise ValueError(
            f"No se encontro un tipo de licencia con nombre '{current_name}' usando lang='{lookup_lang}'"
        )

    if len(result) > 1:
        ids = [str(item["id"]) for item in result]
        raise ValueError(
            f"Se encontraron multiples tipos de licencia con ese nombre. IDs: {', '.join(ids)}"
        )

    return int(result[0]["id"])


def read_leave_type(
    connection: dict[str, Any],
    leave_type_id: int,
    lang: str,
) -> dict[str, Any]:
    result = connection["models"].execute_kw(
        connection["ODOO_DB"],
        connection["uid"],
        connection["ODOO_PASSWORD"],
        "hr.leave.type",
        "search_read",
        [[["id", "=", leave_type_id]]],
        {
            "fields": ["id", "name", "active", "company_id", "write_date"],
            "limit": 1,
            "context": {"lang": lang},
        },
    )

    if not result:
        raise ValueError(f"No se encontro el tipo de licencia con ID {leave_type_id}")

    return result[0]


def write_leave_type_name(
    connection: dict[str, Any],
    leave_type_id: int,
    new_name: str,
    lang: str,
) -> None:
    updated = connection["models"].execute_kw(
        connection["ODOO_DB"],
        connection["uid"],
        connection["ODOO_PASSWORD"],
        "hr.leave.type",
        "write",
        [[leave_type_id], {"name": new_name}],
        {
            "context": {"lang": lang},
        },
    )

    if not updated:
        raise RuntimeError(
            f"Odoo no confirmo la actualizacion del tipo de licencia ID {leave_type_id}"
        )


def resolve_leave_type_id(args: argparse.Namespace, connection: dict[str, Any]) -> int:
    if args.id:
        return args.id

    if args.current_name:
        return search_leave_type_id(connection, args.current_name, args.lookup_lang)

    raise ValueError("Debes indicar --id o --current-name")


def main() -> int:
    args = parse_args()

    try:
        connection = get_connection()
        leave_type_id = resolve_leave_type_id(args, connection)

        before_base = read_leave_type(connection, leave_type_id, args.base_lang)
        before_translation = read_leave_type(connection, leave_type_id, args.translation_lang)

        print("Tipo de licencia encontrado")
        print("=" * 30)
        print(f"ID: {leave_type_id}")
        print(f"Base [{args.base_lang}]: {before_base['name']}")
        print(f"Traduccion [{args.translation_lang}]: {before_translation['name']}")
        print(f"Nuevo nombre: {args.new_name}")

        if args.dry_run:
            print("\nDry run: no se realizaron cambios.")
            return 0

        write_leave_type_name(connection, leave_type_id, args.new_name, args.base_lang)

        if args.sync_translation:
            write_leave_type_name(
                connection,
                leave_type_id,
                args.new_name,
                args.translation_lang,
            )

        after_base = read_leave_type(connection, leave_type_id, args.base_lang)
        after_translation = read_leave_type(connection, leave_type_id, args.translation_lang)

        print("\nActualizacion completada")
        print("=" * 30)
        print(f"Base [{args.base_lang}]: {after_base['name']}")
        print(f"Traduccion [{args.translation_lang}]: {after_translation['name']}")

        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
