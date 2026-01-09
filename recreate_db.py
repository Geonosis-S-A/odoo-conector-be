#!/usr/bin/env python3
"""
Script temporal para recrear la base de datos con todos los modelos.
"""

# Importar todos los modelos para que SQLModel los registre
from app.users.infra.db.models import UserModel
from app.auth.infra.db.models import OTPModel, RefreshTokenModel
from app.personal_time.infra.db.models import (
    TimeOffSyncMappingModel,
    TimeOffSyncLogModel,
)

# Importar SQLModel y engine
from sqlmodel import SQLModel
from app.shared.infra.db.session import engine


def main():
    SQLModel.metadata.drop_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()
