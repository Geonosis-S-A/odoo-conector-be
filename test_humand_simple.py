#!/usr/bin/env python3
"""
Script simple y directo para probar HUMAND Gateway y sincronización de estados.
Modifica las variables al inicio según tus necesidades.
"""

from datetime import date, datetime, timedelta
from app.personal_time.infra.external.humand_gateway import HumandAPIGateway


# ============================================================================
# CONFIGURA TUS OPCIONES AQUÍ
# ============================================================================

# MODO: "gateway", "sync_status", "sync_new", o "sync_full"
# - "gateway": Prueba simple del gateway de Humand (solo consulta)
# - "sync_new": Sincroniza nuevas solicitudes desde Humand a Odoo
# - "sync_status": Actualiza estados de solicitudes ya sincronizadas
# - "sync_full": Ejecuta primero sync_new y luego sync_status
MODO = "sync_new"  # Cambia según necesites

# ============================================================================
# CONFIGURACIÓN PARA MODO "gateway"
# ============================================================================

# page (integer) - Page for pagination (OBLIGATORIO)
PAGE = 1

# limit (integer) - Limit for pagination (OBLIGATORIO)
LIMIT = 10

# states (string) - Used to get results by states
# Valores posibles: "approved", "pending", "rejected"
# Ejemplo: "approved,pending" para multiples estados
STATES = None  # No se usa en esta petición

# policyTypeIds (string) - Used to get results by policy type ids
# Ejemplo: "123,456" para multiples IDs
POLICY_TYPE_IDS = None  # No se usa en esta petición

# fromDate (string $date) - Retrieve results based on a starting date
# Includes all requests with days from this date onwards
# Formato: YYYY-MM-DD
FROM_DATE = date(2022, 1, 1)

# toDate (string $date) - Retrieve results based on end date
# Includes all requests up to and including this date
# Formato: YYYY-MM-DD
TO_DATE = date(2030, 1, 1)

# resolutionFromDate (string $date) - Retrieve results for which the review 
# process ended after this date. Includes all requests with resolution date 
# from this date onwards
# Formato: YYYY-MM-DD
RESOLUTION_FROM_DATE = None  # No se usa en esta petición

# resolutionToDate (string $date) - Retrieve results for which the review 
# process before after this date. Includes all requests with resolution date 
# up to and including this date
# Formato: YYYY-MM-DD
RESOLUTION_TO_DATE = date(2030, 1, 1)

# createdAtSince (string $date) - Retrieve results created on or after this date
# Includes all requests with creation date from this date onwards
# Formato: YYYY-MM-DD
CREATED_AT_SINCE = date(2022, 1, 1)

# ============================================================================
# CONFIGURACIÓN PARA MODO "sync_new"
# ============================================================================

# createdAtSince para sincronización de nuevas solicitudes
# Fecha desde la cual buscar nuevas solicitudes a sincronizar
# Si es None, busca todas las solicitudes
SYNC_NEW_CREATED_AT_SINCE = date(2024, 1, 1)  # Cambia según necesites

# ============================================================================
# CONFIGURACIÓN PARA MODO "sync_status"
# ============================================================================

# resolutionFromDate para sincronización de estados
# Fecha desde la cual buscar solicitudes con cambios de estado
# IMPORTANTE: Solo actualiza solicitudes que ya fueron sincronizadas previamente
# Si es None, busca todas las solicitudes
SYNC_RESOLUTION_FROM_DATE = date(2024, 1, 1)  # Cambia según necesites

# ============================================================================


def test_gateway_simple():
    """Prueba simple del gateway de Humand (solo consulta)."""
    print("=" * 80)
    print("HUMAND GATEWAY - TEST SIMPLE")
    print("=" * 80)
    
    print("\nConfiguracion:")
    print(f"  Pagina (page): {PAGE}")
    print(f"  Limite (limit): {LIMIT}")
    print(f"  Estados (states): {STATES}")
    print(f"  IDs tipos politica (policyTypeIds): {POLICY_TYPE_IDS}")
    print(f"  Desde (fromDate): {FROM_DATE}")
    print(f"  Hasta (toDate): {TO_DATE}")
    print(f"  Resolucion desde (resolutionFromDate): {RESOLUTION_FROM_DATE}")
    print(f"  Resolucion hasta (resolutionToDate): {RESOLUTION_TO_DATE}")
    print(f"  Creadas desde (createdAtSince): {CREATED_AT_SINCE}")
    
    print("\nConsultando HUMAND API...")
    
    try:
        # Inicializar gateway
        gateway = HumandAPIGateway()
        
        # Obtener solicitudes
        requests = gateway.get_all_timeoff_requests(
            page=PAGE,
            limit=LIMIT,
            states=STATES,
            policy_type_ids=POLICY_TYPE_IDS,
            from_date=FROM_DATE,
            to_date=TO_DATE,
            resolution_from_date=RESOLUTION_FROM_DATE,
            resolution_to_date=RESOLUTION_TO_DATE,
            created_at_since=CREATED_AT_SINCE,
        )
        
        print(f"Exito! Obtenidas {len(requests)} solicitudes\n")
        
        # Mostrar resultados
        print("=" * 80)
        print("RESULTADOS")
        print("=" * 80)
        
        for i, req in enumerate(requests, 1):
            print(f"\n{i}. ID: {req.id}")
            print(f"   Usuario: {req.user_name} ({req.user_email})")
            print(f"   Tipo: {req.policy_type_name}")
            print(f"   Periodo: {req.from_date} -> {req.to_date}")
            print(f"   Dias: {req.days}")
            print(f"   Estado: {req.status}")
            if req.reason:
                print(f"   Motivo: {req.reason}")
        
        # Estadisticas
        print("\n" + "=" * 80)
        print("ESTADISTICAS")
        print("=" * 80)
        
        total_dias = sum(req.days for req in requests)
        print(f"Total de días solicitados: {total_dias}")
        
        estados = {}
        for req in requests:
            estados[req.status] = estados.get(req.status, 0) + 1
        
        print("\nPor estado:")
        for estado, cantidad in estados.items():
            print(f"  {estado}: {cantidad}")
        
        tipos = {}
        for req in requests:
            tipos[req.policy_type_name] = tipos.get(req.policy_type_name, 0) + 1
        
        print("\nPor tipo:")
        for tipo, cantidad in tipos.items():
            print(f"  {tipo}: {cantidad}")
        
        print("\nTest completado exitosamente!\n")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


def test_sync_status_updates():
    """Prueba la sincronización de actualizaciones de estado."""
    print("=" * 80)
    print("SYNC STATUS UPDATES - TEST")
    print("=" * 80)
    
    print(f"\nBuscando solicitudes con cambios de estado desde: {SYNC_RESOLUTION_FROM_DATE}")
    
    try:
        from sqlmodel import Session, SQLModel
        from app.shared.infra.db.session import engine
        from app.shared.infra.external.odoo.odoo_client import OdooClient
        from app.personal_time.infra.external.odoo_timeoff_type_gateway import OdooTimeOffeGateway
        from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
        from app.personal_time.infra.db.repositories import SQLModelTimeOffSyncMappingRepository
        from app.personal_time.application.use_cases.sync_new_timeoff_requests import (
            SyncNewTimeOffRequestsUseCase,
        )
        
        # Importar todos los modelos para que SQLModel los registre
        from app.users.infra.db.models import UserModel
        from app.auth.infra.db.models import OTPModel, RefreshTokenModel
        from app.personal_time.infra.db.models import (
            TimeOffSyncMappingModel,
            TimeOffSyncLogModel,
        )
        
        # 0. Crear las tablas si no existen (solo en entorno LOCAL)
        print("\n[0/6] Verificando/Creando tablas en la base de datos...")
        import os
        env = os.getenv("ENV", "LOCAL")
        if env == "LOCAL":
            SQLModel.metadata.create_all(bind=engine)
            print("   Tablas creadas/verificadas correctamente")
        
        # 1. Configurar la sesión de base de datos
        print("\n[1/6] Configurando sesión de base de datos...")
        with Session(engine) as db_session:
            
            # 2. Configurar conexión a Odoo
            print("[2/6] Configurando conexión a Odoo...")
            odoo_client = OdooClient()
            odoo_client.authenticate()
            odoo_connection = odoo_client.get_connection()
            
            # 3. Inicializar gateways y repositorios
            print("[3/6] Inicializando gateways y repositorios...")
            humand_gateway = HumandAPIGateway()
            odoo_gateway = OdooTimeOffeGateway(odoo_connection)
            employee_gateway = OdooEmployeeGateway(odoo_connection)
            mapping_repository = SQLModelTimeOffSyncMappingRepository(db_session)
            
            # 4. Crear el use case
            print("[4/6] Creando use case...")
            use_case = SyncNewTimeOffRequestsUseCase(
                humand_gateway=humand_gateway,
                odoo_gateway=odoo_gateway,
                employee_gateway=employee_gateway,
                mapping_repository=mapping_repository,
            )
            
            # 5. Ejecutar sincronización de estados
            print("[5/6] Ejecutando sincronización de estados...")
            print("-" * 80)
            
            resolution_from_datetime = datetime.combine(
                SYNC_RESOLUTION_FROM_DATE, 
                datetime.min.time()
            ) if SYNC_RESOLUTION_FROM_DATE else None
            
            result = use_case.sync_status_updates(
                resolution_from_date=resolution_from_datetime
            )
            
            # Mostrar resultados
            print("-" * 80)
            print("\n" + "=" * 80)
            print("RESULTADOS DE LA SINCRONIZACIÓN DE ESTADOS")
            print("=" * 80)
            
            print(f"\nResumen:")
            print(f"   - Total procesadas:           {result.total_processed}")
            print(f"   - Actualizaciones exitosas:  {result.status_updates_count}")
            print(f"   - Saltadas (sin cambios):     {result.skipped_count}")
            print(f"   - Errores:                    {result.errors_count}")
            
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
                # Verificar si todos los errores son por falta de mapeo
                all_no_mapping = all(
                    "No se encontró mapeo" in error_msg 
                    for _, error_msg in result.errors
                )
                if all_no_mapping:
                    print("\n[INFO] Todos los errores son por falta de mapeo.")
                    print("       Esto significa que las solicitudes no han sido sincronizadas previamente.")
                    print("       Ejecuta primero el modo 'sync_new' o 'sync_full' para crear los mapeos.")
            
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


def test_sync_new_requests():
    """Sincroniza nuevas solicitudes desde Humand a Odoo."""
    print("=" * 80)
    print("SYNC NEW REQUESTS - TEST")
    print("=" * 80)
    
    print(f"\nBuscando nuevas solicitudes creadas desde: {SYNC_NEW_CREATED_AT_SINCE}")
    
    try:
        from sqlmodel import Session, SQLModel
        from app.shared.infra.db.session import engine
        from app.shared.infra.external.odoo.odoo_client import OdooClient
        from app.personal_time.infra.external.odoo_timeoff_type_gateway import OdooTimeOffeGateway
        from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
        from app.personal_time.infra.db.repositories import SQLModelTimeOffSyncMappingRepository
        from app.personal_time.application.use_cases.sync_new_timeoff_requests import (
            SyncNewTimeOffRequestsUseCase,
        )
        
        # Importar todos los modelos para que SQLModel los registre
        from app.users.infra.db.models import UserModel
        from app.auth.infra.db.models import OTPModel, RefreshTokenModel
        from app.personal_time.infra.db.models import (
            TimeOffSyncMappingModel,
            TimeOffSyncLogModel,
        )
        
        # 0. Crear las tablas si no existen (solo en entorno LOCAL)
        print("\n[0/5] Verificando/Creando tablas en la base de datos...")
        import os
        env = os.getenv("ENV", "LOCAL")
        if env == "LOCAL":
            SQLModel.metadata.create_all(bind=engine)
            print("   Tablas creadas/verificadas correctamente")
        
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
            
            # 5. Ejecutar sincronización de nuevas solicitudes
            print("[5/5] Ejecutando sincronización de nuevas solicitudes...")
            print("-" * 80)
            
            created_at_datetime = datetime.combine(
                SYNC_NEW_CREATED_AT_SINCE, 
                datetime.min.time()
            ) if SYNC_NEW_CREATED_AT_SINCE else None
            
            result = use_case.execute(created_at_since=created_at_datetime)
            
            # Mostrar resultados
            print("-" * 80)
            print("\n" + "=" * 80)
            print("RESULTADOS DE LA SINCRONIZACIÓN DE NUEVAS SOLICITUDES")
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
                print("\n[OK] Sincronización completada exitosamente!")
            elif result.successfully_synced > 0 and result.errors_count > 0:
                print("\n[WARNING] Sincronización completada con algunos errores")
            elif result.total_processed == 0:
                print("\n[INFO] No hay solicitudes nuevas para sincronizar")
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


def test_sync_full():
    """Ejecuta sincronización completa: primero nuevas solicitudes, luego actualización de estados."""
    print("=" * 80)
    print("SYNC FULL - TEST (Nuevas solicitudes + Actualización de estados)")
    print("=" * 80)
    
    print("\nEste modo ejecutará:")
    print("  1. Sincronización de nuevas solicitudes")
    print("  2. Actualización de estados de solicitudes sincronizadas")
    
    # Ejecutar sincronización de nuevas solicitudes
    print("\n" + "=" * 80)
    print("PASO 1: Sincronización de nuevas solicitudes")
    print("=" * 80)
    result_new = test_sync_new_requests()
    
    if result_new != 0:
        print("\n[WARNING] La sincronización de nuevas solicitudes tuvo errores.")
        print("         Continuando con la actualización de estados...")
    
    # Ejecutar actualización de estados
    print("\n" + "=" * 80)
    print("PASO 2: Actualización de estados")
    print("=" * 80)
    result_status = test_sync_status_updates()
    
    # Resultado final
    print("\n" + "=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)
    
    if result_new == 0 and result_status == 0:
        print("\n[OK] Sincronización completa exitosa!")
        return 0
    elif result_new == 0 or result_status == 0:
        print("\n[WARNING] Sincronización completa con algunos errores")
        return 1
    else:
        print("\n[ERROR] Sincronización completa falló")
        return 1


def main():
    """Función principal que ejecuta el modo seleccionado."""
    if MODO == "gateway":
        return test_gateway_simple()
    elif MODO == "sync_new":
        return test_sync_new_requests()
    elif MODO == "sync_status":
        return test_sync_status_updates()
    elif MODO == "sync_full":
        return test_sync_full()
    else:
        print(f"\n[ERROR] Modo inválido: {MODO}")
        print("Modos válidos: 'gateway', 'sync_new', 'sync_status', o 'sync_full'")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

