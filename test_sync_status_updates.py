#!/usr/bin/env python3
"""
Script de prueba para la sincronización de actualizaciones de estado.

Este script demuestra cómo usar el nuevo método execute_status_sync()
para sincronizar cambios de estado desde Humand a Odoo.
"""
from datetime import datetime, date, timedelta
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
    """Ejecuta la sincronización de estados modificados."""
    
    print("=" * 80)
    print("TEST: Sincronización de Actualizaciones de Estado")
    print("=" * 80)
    
    # Fecha desde la cual buscar cambios (últimas 24 horas)
    resolution_since = datetime.now() - timedelta(days=1)
    
    print(f"\nBuscando solicitudes modificadas desde: {resolution_since.date()}")
    print(f"Nota: Se sincronizarán los estados de licencias que cambiaron en Humand")
    
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
            
            # 5. Ejecutar sincronización de estados
            print("[5/5] Ejecutando sincronización de estados...")
            print(f"     Filtrando solo Humand ID: 1309124")
            print("-" * 80)
            
            # Obtener todas las solicitudes y filtrar solo la que nos interesa
            from app.personal_time.application.use_cases.sync_new_timeoff_requests import SyncResult
            
            result = SyncResult()
            
            # Obtener todas las solicitudes modificadas
            all_requests = humand_gateway.get_all_timeoff_requests(
                resolution_from_date=resolution_since.date()
            )
            
            print(f"     Total de solicitudes obtenidas: {len(all_requests)}")
            
            # Filtrar solo la solicitud específica
            target_request = None
            for req in all_requests:
                if req.id == "1309124":
                    target_request = req
                    break
            
            if target_request:
                print(f"     ✓ Encontrada solicitud Humand ID: {target_request.id}")
                print(f"       - Usuario: {target_request.user_name} ({target_request.user_email})")
                print(f"       - Tipo: {target_request.policy_type_name}")
                print(f"       - Estado actual en Humand: {target_request.status}")
                print(f"       - Fechas: {target_request.from_date} → {target_request.to_date}")
                print()
                
                # Procesar solo esta solicitud
                use_case._process_single_status_update(target_request, result)
            else:
                print(f"     ✗ No se encontró la solicitud con Humand ID: 1308078")
                print(f"       Solicitudes disponibles: {[req.id for req in all_requests[:10]]}")
                result.add_error("1308078", "Solicitud no encontrada en Humand")
            
            # Mostrar resultados
            print("-" * 80)
            print("\n" + "=" * 80)
            print("RESULTADOS DE LA SINCRONIZACIÓN DE ESTADOS")
            print("=" * 80)
            
            print(f"\nResumen:")
            print(f"   - Total procesadas:         {result.total_processed}")
            print(f"   - Estados actualizados:     {result.status_updates_count}")
            print(f"   - Saltadas (sin cambios):   {result.skipped_count}")
            print(f"   - Errores:                  {result.errors_count}")
            
            if result.errors:
                print(f"\nErrores encontrados ({len(result.errors)}):")
                for humand_id, error_msg in result.errors:
                    print(f"   - Humand ID {humand_id}: {error_msg}")
            
            # Mostrar estado final
            if result.errors_count == 0 and result.total_processed > 0:
                print("\n[OK] Sincronización de estados completada exitosamente!")
            elif result.status_updates_count > 0 and result.errors_count > 0:
                print("\n[WARNING] Sincronización completada con algunos errores")
            elif result.total_processed == 0:
                print("\n[INFO] No hay solicitudes con cambios de estado para sincronizar")
            else:
                print("\n[ERROR] La sincronización falló")
            
            print("\n" + "=" * 80)
            
            return 0 if result.errors_count == 0 else 1
            
    except KeyboardInterrupt:
        print("\n\n[WARNING] Sincronización interrumpida por el usuario")
        return 130
        
    except Exception as e:
        print(f"\n[ERROR] Error fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
