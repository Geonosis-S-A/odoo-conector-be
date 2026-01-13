#!/usr/bin/env python3
"""
Script simple y directo para probar HUMAND Gateway.
Modifica las variables al inicio según tus necesidades.
"""

from datetime import date, timedelta
from app.personal_time.infra.external.humand_gateway import HumandAPIGateway


# ============================================================================
# CONFIGURA TUS FILTROS AQUÍ
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


def main():
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
        
    except Exception as e:
        print(f"\nError: {e}\n")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

