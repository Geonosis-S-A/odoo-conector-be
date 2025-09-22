#!/usr/bin/env python3
"""
Script de prueba para el nuevo endpoint de creación de solicitudes de tiempo personal.
"""

import requests
import json
from datetime import date, timedelta

# Configuración del endpoint
BASE_URL = "http://localhost:8000"  # Ajustar según tu configuración
ENDPOINT = f"{BASE_URL}/personal-time/timeoff-requests"

def test_endpoint():
    """Prueba el endpoint de creación de solicitudes de tiempo personal."""
    
    print("🧪 Testing TimeOff Request Endpoint")
    print("=" * 50)
    
    # Datos de prueba
    tomorrow = date.today() + timedelta(days=1)
    day_after_tomorrow = date.today() + timedelta(days=2)
    
    request_data = {
        "holiday_status_id": 2,  # Sick Time Off
        "request_date_from": tomorrow.strftime("%Y-%m-%d"),
        "request_date_to": day_after_tomorrow.strftime("%Y-%m-%d"),
        "description": "Solicitud de prueba desde script Python"
    }
    
    headers = {
        "Content-Type": "application/json",
        # Nota: En producción necesitarías agregar headers de autenticación
        # "Authorization": "Bearer <tu_token_jwt>"
    }
    
    print(f"📋 Datos de la solicitud:")
    print(f"   Tipo de licencia ID: {request_data['holiday_status_id']}")
    print(f"   Desde: {request_data['request_date_from']}")
    print(f"   Hasta: {request_data['request_date_to']}")
    print(f"   Descripción: {request_data['description']}")
    print()
    
    try:
        print("🚀 Enviando solicitud al endpoint...")
        response = requests.post(ENDPOINT, json=request_data, headers=headers)
        
        print(f"📊 Respuesta:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.content:
            try:
                data = response.json()
                print(f"   Response Body:")
                print(f"   {json.dumps(data, indent=4, ensure_ascii=False)}")
                
                if response.status_code == 201:
                    print("\n✅ ¡Solicitud creada exitosamente!")
                    if data.get("request_id"):
                        print(f"   ID de solicitud: {data['request_id']}")
                    print(f"   Mensaje: {data.get('message', 'N/A')}")
                        
                elif response.status_code == 400:
                    print("\n⚠️  Error de validación (esperado sin autenticación)")
                    print(f"   Detalle: {data.get('detail', 'N/A')}")
                    
                elif response.status_code == 401:
                    print("\n🔒 Error de autenticación (esperado)")
                    print("   Para usar este endpoint necesitas:")
                    print("   1. Estar autenticado con un JWT válido")
                    print("   2. Tener permisos de empleado")
                    
                elif response.status_code == 422:
                    print("\n❌ Error de validación de datos")
                    print(f"   Detalle: {data.get('detail', 'N/A')}")
                    
                else:
                    print(f"\n❓ Respuesta inesperada: {response.status_code}")
                    
            except json.JSONDecodeError:
                print(f"   Response Body (raw): {response.text}")
        else:
            print("   Response Body: (vacío)")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión!")
        print("   Asegúrate de que el servidor FastAPI esté ejecutándose en:")
        print(f"   {BASE_URL}")
        print("\n   Para iniciar el servidor, ejecuta:")
        print("   uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

    print("\n" + "=" * 50)
    print("📖 Documentación del endpoint:")
    print(f"   Swagger UI: {BASE_URL}/docs")
    print(f"   ReDoc: {BASE_URL}/redoc")
    print("\n📝 Ejemplo de uso con curl:")
    print(f'''
curl -X POST "{ENDPOINT}" \\
     -H "Content-Type: application/json" \\
     -H "Authorization: Bearer <tu_token_jwt>" \\
     -d '{json.dumps(request_data, ensure_ascii=False)}'
    ''')

if __name__ == "__main__":
    test_endpoint()
