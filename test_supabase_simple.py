#!/usr/bin/env python3
"""
Script simple para probar la conexión a Supabase usando librerías estándar
"""

import sys
import socket
import urllib.parse
from datetime import datetime

# URL de conexión a Supabase
DATABASE_URL = "postgresql://postgres.oxqymizcppaufesongap:Lafacupibe01@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"


def parse_database_url(url):
    """Parsea la URL de la base de datos"""
    parsed = urllib.parse.urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port,
        "database": parsed.path.lstrip("/"),
        "username": parsed.username,
        "password": parsed.password,
    }


def test_network_connection():
    """Prueba la conectividad de red al servidor"""
    print("🔧 Probando conectividad de red...")

    try:
        db_info = parse_database_url(DATABASE_URL)
        host = db_info["host"]
        port = db_info["port"]

        print(f"🌐 Conectando a: {host}:{port}")

        # Crear socket y probar conexión
        start_time = datetime.now()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # Timeout de 10 segundos

        result = sock.connect_ex((host, port))
        end_time = datetime.now()

        sock.close()

        if result == 0:
            latency = (end_time - start_time).total_seconds()
            print(f"✅ Conexión TCP exitosa! Latencia: {latency:.3f}s")
            return True
        else:
            print(f"❌ No se pudo conectar al servidor. Código de error: {result}")
            return False

    except socket.gaierror as e:
        print(f"❌ Error de resolución DNS: {e}")
        return False
    except Exception as e:
        print(f"❌ Error de red: {e}")
        return False


def show_connection_info():
    """Muestra información de la conexión"""
    print("\n📋 Información de conexión:")
    print("=" * 40)

    try:
        db_info = parse_database_url(DATABASE_URL)

        print(f"🏠 Host: {db_info['host']}")
        print(f"🔌 Puerto: {db_info['port']}")
        print(f"💾 Base de datos: {db_info['database']}")
        print(f"👤 Usuario: {db_info['username']}")
        print(
            f"🔐 Contraseña: {'*' * len(db_info['password']) if db_info['password'] else 'No configurada'}"
        )

        return True

    except Exception as e:
        print(f"❌ Error al parsear URL: {e}")
        return False


def test_dns_resolution():
    """Prueba la resolución DNS del servidor"""
    print("\n🔧 Probando resolución DNS...")

    try:
        db_info = parse_database_url(DATABASE_URL)
        host = db_info["host"]

        # Resolver la dirección IP
        ip_address = socket.gethostbyname(host)
        print(f"✅ DNS resuelto: {host} -> {ip_address}")

        return True

    except socket.gaierror as e:
        print(f"❌ Error de DNS: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Función principal"""
    print("🚀 Prueba básica de conectividad a Supabase")
    print("=" * 50)

    results = []

    # Ejecutar pruebas básicas
    results.append(show_connection_info())
    results.append(test_dns_resolution())
    results.append(test_network_connection())

    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS BÁSICAS")
    print("=" * 50)

    passed = sum(results)
    total = len(results)

    print(f"✅ Pruebas exitosas: {passed}/{total}")
    print(f"❌ Pruebas fallidas: {total - passed}/{total}")

    if all(results):
        print("🎉 ¡Conectividad básica exitosa!")
        print("💡 Para pruebas completas de PostgreSQL, ejecuta:")
        print("   python test_supabase_connection.py")
    else:
        print("⚠️  Problemas de conectividad detectados.")

    print(f"\n📝 Nota: Este script solo prueba conectividad de red.")
    print(f"   Para probar la conexión completa a PostgreSQL,")
    print(f"   asegúrate de tener asyncpg instalado y ejecuta el script completo.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Pruebas interrumpidas por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)
