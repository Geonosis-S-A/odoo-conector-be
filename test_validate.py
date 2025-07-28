import os
from dotenv import load_dotenv
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)

# Cargar variables de entorno desde .env
load_dotenv()


def test_validate_timesheet():
    """
    Script para probar la validación de timesheets en Odoo.
    """
    try:
        # --- Configuración ---
        # IDs de las líneas de timesheet que quieres validar
        # CAMBIA ESTO POR IDs REALES DE TU INSTANCIA DE ODOO
        timesheet_ids_to_validate = [1490]  # <--- MODIFICA ESTA LÍNEA

        print("Conectando con Odoo...")
        odoo_connection = get_odoo_connection()
        print("Conexión exitosa.")

        timesheet_gateway = OdooTimesheetLineGateway(odoo_connection)

        # --- Ejecución del método ---
        print(f"Validando timesheets con IDs: {timesheet_ids_to_validate}...")
        success = timesheet_gateway.validate(timesheet_ids_to_validate)

        # --- Verificación ---
        if success:
            print("¡La validación se ejecutó correctamente en Odoo!")
        else:
            print("La validación falló. Revisa los logs de Odoo para más detalles.")

    except Exception as e:
        print(f"Ocurrió un error: {e}")


if __name__ == "__main__":
    test_validate_timesheet()
