#!/usr/bin/env python3
"""
Script para probar el SyncNewTimeOffRequestsUseCase.
Prueba la sincronización de solicitudes de licencias desde Humand a Odoo
para las solicitudes creadas hoy (09/01/2026).
"""

from datetime import datetime, date
from sqlmodel import Session

from app.shared.infra.db.session import engine
from app.shared.infra.external.odoo.odoo_client import OdooClient
from app.personal_time.infra.external.humand_gateway import HumandAPIGateway
from app.personal_time.infra.external.odoo_timeoff_type_gateway import OdooTimeOffeGateway
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.personal_time.infra.db.repositories import SQLModelTimeOffSyncMappingRepository
from app.personal_time.application.use_cases.sync_new_timeoff_requests import (
    SyncNewTimeOffRequestsUseCase,
)


def main():
    print("=" * 80)
    print("TEST: SyncNewTimeOffRequestsUseCase")
    print("=" * 80)
    
    # Fecha de prueba: usar una fecha histórica real (2024)
    # para evitar problemas con fechas futuras en el API de Humand
    from datetime import timedelta
    search_from = date(2024, 12, 1)  # Diciembre 2024
    created_at_since = datetime.combine(search_from, datetime.min.time())
    
    print(f"\nBuscando solicitudes creadas desde: {search_from}")
    print(f"Nota: Usando fecha historica para prueba (el API no acepta fechas futuras)")
    
    try:
        # 1. Configurar la sesión de base de datos
        print("\n[1/5] Configurando sesión de base de datos...")
        with Session(engine) as db_session:
            
            # 2. Configurar conexión a Odoo
            print("[2/5] Configurando conexión a Odoo...")
            odoo_client = OdooClient()
            odoo_client.authenticate()
            odoo_connection = odoo_client.get_connection()
            
            # 3. Inicializar gateways y repositorios
            print("[3/5] Inicializando gateways y repositorios...")
            humand_gateway = HumandAPIGateway()
            odoo_gateway = OdooTimeOffeGateway(odoo_connection)
            employee_gateway = OdooEmployeeGateway(odoo_connection)
            mapping_repository = SQLModelTimeOffSyncMappingRepository(db_session)
            
            # 4. Crear el use case
            print("[4/5] Creando use case...")
            use_case = SyncNewTimeOffRequestsUseCase(
                humand_gateway=humand_gateway,
                odoo_gateway=odoo_gateway,
                employee_gateway=employee_gateway,
                mapping_repository=mapping_repository,
            )
            
            # 5. Ejecutar sincronización
            print("[5/5] Ejecutando sincronización...")
            print("-" * 80)
            
            result = use_case.execute(created_at_since=created_at_since)
            
            # Mostrar resultados
            print("-" * 80)
            print("\n" + "=" * 80)
            print("RESULTADOS DE LA SINCRONIZACIÓN")
            print("=" * 80)
            
            print(f"\nResumen:")
            print(f"   - Total procesadas:     {result.total_processed}")
            print(f"   - Sincronizadas:        {result.successfully_synced}")
            print(f"   - Saltadas (ya existian): {result.skipped_count}")
            print(f"   - Errores:              {result.errors_count}")
            
            if result.errors:
                print(f"\nErrores encontrados ({len(result.errors)}):")
                for humand_id, error_msg in result.errors:
                    print(f"   - Humand ID {humand_id}: {error_msg}")
            
            # Mostrar estado final
            if result.errors_count == 0 and result.total_processed > 0:
                print("\n[OK] Sincronizacion completada exitosamente!")
            elif result.successfully_synced > 0 and result.errors_count > 0:
                print("\n[WARNING] Sincronizacion completada con algunos errores")
            elif result.total_processed == 0:
                print("\n[INFO] No hay solicitudes nuevas para sincronizar")
            else:
                print("\n[ERROR] La sincronizacion fallo")
            
            print("\n" + "=" * 80)
            
            return 0 if result.errors_count == 0 else 1
            
    except KeyboardInterrupt:
        print("\n\n[WARNING] Sincronizacion interrumpida por el usuario")
        return 130
        
    except Exception as e:
        print(f"\n[ERROR] Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
