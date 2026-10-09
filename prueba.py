#!/usr/bin/env python3
"""
Script limpio para crear tiempo personal en Odoo
Versión simplificada sin errores de tipado
"""

import os
import sys
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
import xmlrpc.client

# Agregar el directorio raíz del proyecto al PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from app.shared.infra.external.odoo.odoo_client import get_odoo_credentials

    USE_PROJECT_CONFIG = True
except ImportError:
    print(
        "⚠️  No se encontró la configuración del proyecto, usando configuración manual"
    )
    USE_PROJECT_CONFIG = False


def get_manual_credentials() -> Dict[str, str]:
    """Configuración manual si no está disponible la del proyecto"""
    load_dotenv()

    required_vars = ["ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_PASSWORD"]
    credentials = {}

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            raise ValueError(f"Variable de entorno {var} no definida")
        credentials[var.lower().replace("odoo_", "")] = value

    return credentials


def obtener_tipos_ausencias(
    models, db: str, uid: int, password: str
) -> List[Dict[str, Any]]:
    """Obtiene los tipos de ausencias disponibles"""
    print("📋 Consultando tipos de ausencias...")

    try:
        result = models.execute_kw(
            db,
            uid,
            password,
            "hr.leave.type",
            "search_read",
            [[]],
            {"fields": ["id", "name"], "limit": 10},
        )

        print("🏷️  Tipos disponibles:")
        print("-" * 30)
        for tipo in result:
            print(f"ID: {tipo['id']:2d} - {tipo['name']}")

        return result
    except Exception as e:
        print(f"❌ Error al obtener tipos: {e}")
        return []


def verificar_empleado(
    models, db: str, uid: int, password: str, employee_id: int
) -> bool:
    """Verifica que el empleado existe"""
    print(f"👤 Verificando empleado ID {employee_id}...")

    try:
        result = models.execute_kw(
            db,
            uid,
            password,
            "hr.employee",
            "search_read",
            [[("id", "=", employee_id)]],
            {"fields": ["id", "name", "work_email"]},
        )

        if result:
            empleado = result[0]
            print(
                f"✅ Empleado: {empleado['name']} ({empleado.get('work_email', 'Sin email')})"
            )
            return True
        else:
            print(f"❌ No existe empleado con ID {employee_id}")
            return False
    except Exception as e:
        print(f"❌ Error al verificar empleado: {e}")
        return False


def crear_solicitud_ausencia(
    models,
    db: str,
    uid: int,
    password: str,
    employee_id: int,
    tipo_ausencia_id: int,
    fecha_inicio: date,
    fecha_fin: date,
    descripcion: str = "Tiempo personal - Prueba",
) -> Optional[int]:
    """Crea una solicitud de ausencia"""

    print("\n🕐 Creando solicitud de ausencia...")
    print(f"   Empleado: {employee_id}")
    print(f"   Tipo: {tipo_ausencia_id}")
    print(f"   Desde: {fecha_inicio}")
    print(f"   Hasta: {fecha_fin}")

    try:
        datos_solicitud = {
            "holiday_status_id": tipo_ausencia_id,
            "name": descripcion,
            "request_date_from": fecha_inicio.strftime("%Y-%m-%d"),
            "request_date_to": fecha_fin.strftime("%Y-%m-%d"),
            "employee_id": employee_id,
        }

        solicitud_id = models.execute_kw(
            db, uid, password, "hr.leave", "create", [datos_solicitud]
        )

        print(f"✅ Solicitud creada con ID: {solicitud_id}")
        return int(solicitud_id)

    except Exception as e:
        print(f"❌ Error al crear solicitud: {e}")
        return None


def listar_empleados_disponibles(
    models, db: str, uid: int, password: str
) -> List[Dict[str, Any]]:
    """Lista los primeros empleados disponibles para elegir"""
    print("👥 Consultando empleados disponibles...")

    try:
        result = models.execute_kw(
            db,
            uid,
            password,
            "hr.employee",
            "search_read",
            [[]],
            {"fields": ["id", "name", "work_email"], "limit": 10},
        )

        print("🏷️  Empleados disponibles:")
        print("-" * 40)
        for empleado in result:
            email = empleado.get("work_email", "Sin email")
            print(f"ID: {empleado['id']:2d} - {empleado['name']} ({email})")

        return result
    except Exception as e:
        print(f"❌ Error al obtener empleados: {e}")
        return []


def main():
    """Función principal"""
    print("🚀 Creador de Tiempo Personal - Odoo")
    print("=" * 40)

    try:
        # Obtener credenciales
        if USE_PROJECT_CONFIG:
            print("🔧 Usando configuración del proyecto...")
            credentials = get_odoo_credentials()
        else:
            print("🔧 Usando configuración manual...")
            credentials = get_manual_credentials()

        url = credentials["url"]
        db = credentials["db"]
        username = credentials["username"]
        password = credentials["password"]

        print(f"🌐 Conectando a: {url}")
        print(f"📊 Base de datos: {db}")

        # Conectar a Odoo
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

        # Autenticar
        print("🔐 Autenticando...")
        uid = common.authenticate(db, username, password, {})

        if not uid:
            print("❌ Error de autenticación")
            return

        print(f"✅ Autenticado (UID: {uid})")

        # Mostrar empleados disponibles
        print("\n" + "=" * 50)
        empleados = listar_empleados_disponibles(models, db, uid, password)
        if not empleados:
            print("❌ No se encontraron empleados")
            return

        # Configuración de la solicitud - CAMBIA AQUÍ EL ID DEL EMPLEADO
        # Puedes usar cualquier ID de la lista de arriba
        EMPLOYEE_ID = 588  # 🔄 CAMBIA ESTE NÚMERO por el ID que quieras probar

        print(f"\n🎯 Probando con Employee ID: {EMPLOYEE_ID}")
        print("=" * 50)

        # Verificar empleado específico
        if not verificar_empleado(models, db, uid, password, EMPLOYEE_ID):
            print("❌ No se puede continuar con ese empleado")
            print(
                "💡 Cambia el EMPLOYEE_ID en el código por uno de los IDs listados arriba"
            )
            return

        # Obtener tipos de ausencias
        tipos = obtener_tipos_ausencias(models, db, uid, password)
        if not tipos:
            print("❌ No hay tipos de ausencias disponibles")
            return

        # Usar un tipo específico o el primero disponible
        # Puedes cambiar esto para usar un tipo específico
        TIPO_PREFERIDO = 4  # 🔄 CAMBIA ESTE NÚMERO por el tipo que prefieras (4 = Unpaid - no requiere asignación)

        tipo_seleccionado = None
        for tipo in tipos:
            if tipo["id"] == TIPO_PREFERIDO:
                tipo_seleccionado = tipo
                break

        if not tipo_seleccionado:
            print(
                f"⚠️  Tipo de ausencia ID {TIPO_PREFERIDO} no encontrado, usando el primero disponible"
            )
            tipo_seleccionado = tipos[0]

        tipo_id = tipo_seleccionado["id"]
        print(
            f"\n🎯 Usando tipo de ausencia: {tipo_seleccionado['name']} (ID: {tipo_id})"
        )

        # Configurar fechas (próxima semana)
        hoy = date.today()
        inicio = hoy + timedelta(days=7)  # Próxima semana
        fin = inicio + timedelta(days=1)  # 2 días

        print(f"📅 Fechas configuradas: {inicio} a {fin}")

        # Crear solicitud
        solicitud_id = crear_solicitud_ausencia(
            models,
            db,
            uid,
            password,
            employee_id=EMPLOYEE_ID,
            tipo_ausencia_id=tipo_id,
            fecha_inicio=inicio,
            fecha_fin=fin,
            descripcion=f"Tiempo personal - Prueba script para empleado {EMPLOYEE_ID} - {hoy}",
        )

        if solicitud_id:
            print(f"\n🎉 ¡Éxito! Solicitud creada con ID: {solicitud_id}")
            print(
                "💡 Revisa en Odoo: Recursos Humanos > Ausencias > Solicitudes de Ausencia"
            )
            print(f"🔍 Busca por ID de solicitud: {solicitud_id}")
        else:
            print("\n❌ No se pudo crear la solicitud")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
