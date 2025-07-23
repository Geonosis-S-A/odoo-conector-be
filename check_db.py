#!/usr/bin/env python3
"""
Script para verificar el contenido de la base de datos.
"""

from app.users.infra.db.models import UserModel
from app.auth.infra.db.models import OTPModel, RefreshTokenModel
from sqlmodel import SQLModel, Session, select
from app.shared.infra.db.session import engine


def main():
    print("=== Verificando contenido de la base de datos ===\n")

    with Session(engine) as session:
        # Verificar usuarios usando el mismo método que el repositorio
        statement = select(UserModel)
        users = session.exec(statement).all()
        print(f"Usuarios en la base de datos: {len(users)}")
        for user in users:
            print(
                f"  - ID: {user.id}, Email: {user.email}, Name: {user.full_name}, Active: {user.is_active}, Roles: {user.roles}"
            )

        # Verificar OTPs
        statement = select(OTPModel)
        otps = session.exec(statement).all()
        print(f"\nOTPs en la base de datos: {len(otps)}")
        for otp in otps:
            print(f"  - ID: {otp.id}, User ID: {otp.user_id}, Code: {otp.code}")

        # Verificar Refresh Tokens
        statement = select(RefreshTokenModel)
        tokens = session.exec(statement).all()
        print(f"\nRefresh Tokens en la base de datos: {len(tokens)}")
        for token in tokens:
            print(f"  - ID: {token.id}, User ID: {token.user_id}")

    print("\n=== Fin de verificación ===")


if __name__ == "__main__":
    main()
