# 📊 Gestión de Base de Datos

Este documento explica cómo está estructurado el manejo de bases de datos en el proyecto, incluyendo la configuración, migraciones con Alembic y operaciones básicas.

## 🏗️ Arquitectura de Base de Datos

### Stack Tecnológico

- **SQLModel**: Framework que combina SQLAlchemy + Pydantic para definir modelos
- **Alembic**: Herramienta de migración de esquemas de base de datos
- **PostgreSQL**: Base de datos principal para staging y producción
- **SQLite**: Base de datos para desarrollo local y pruebas

## ⚙️ Configuración de Base de Datos

### Variables de Entorno

El proyecto utiliza las siguientes variables de entorno para configurar las conexiones:

```bash
# Entorno actual
ENV=LOCAL  # LOCAL, STAGING, PROD

# Base de datos principal
DATABASE_URL=sqlite:///./app.db  # Para desarrollo local
DATABASE_URL=postgresql://user:password@localhost:5432/dbname  # Para staging/prod

# Base de datos para migraciones
MIGRATION_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

# Base de datos para pruebas
TEST_DATABASE_URL=sqlite:///./test.db
```

### Configuraciones por Entorno

| Entorno | Base de Datos Permitida | Archivo de Configuración        |
| ------- | ----------------------- | ------------------------------- |
| LOCAL   | SQLite / PostgreSQL     | `app/shared/infra/db/config.py` |
| STAGING | Solo PostgreSQL         | `app/shared/infra/db/config.py` |
| PROD    | Solo PostgreSQL         | `app/shared/infra/db/config.py` |

## 🔧 Creación de Tablas por Entorno

El proyecto maneja la creación de tablas de manera diferente según el entorno:

### Entorno LOCAL

En el entorno local, las tablas se crean automáticamente al iniciar la aplicación usando `SQLModel.metadata.create_all()`. Esto se hace en el lifespan de FastAPI:

```python
# app/main.py
@asynccontextmanager
async def lifespan(app):
    if ENV == "LOCAL":
        # En local, creamos las tablas automáticamente
        from sqlmodel import SQLModel
        from app.shared.infra.db.session import engine

        SQLModel.metadata.create_all(bind=engine)
    yield  # acá arranca la app
```

### Entorno STAGING y PRODUCTION

En estos entornos, **NO** se crean las tablas automáticamente. Todas las modificaciones del esquema de base de datos deben manejarse a través de **migraciones con Alembic**.

### ¿Por qué esta diferencia?

| Aspecto          | LOCAL                                | STAGING/PROD                         |
| ---------------- | ------------------------------------ | ------------------------------------ |
| **Conveniencia** | ✅ Automático, ideal para desarrollo | ❌ Manual, pero controlado           |
| **Control**      | ❌ Sin historial de cambios          | ✅ Historial completo de migraciones |
| **Rollback**     | ❌ Difícil revertir cambios          | ✅ Fácil rollback con Alembic        |
| **Colaboración** | ❌ Puede causar inconsistencias      | ✅ Todos tienen el mismo esquema     |
| **Producción**   | ❌ Riesgoso                          | ✅ Seguro y predecible               |

### Flujo de Trabajo Recomendado

1. **Desarrollo Local**: Modifica los modelos y reinicia la app (las tablas se recrean automáticamente)
2. **Antes de subir a staging**: Crea la migración correspondiente con Alembic
3. **En staging/prod**: Aplica las migraciones usando `alembic upgrade head` (o hacerlo por consola antes)

## 🔄 Migraciones con Alembic

### Configuración de Alembic

El archivo `migrations/env.py` está configurado para:

**Hay que importar los modelos que se van a usar para que los detecte, en env.py**

2. **Configuración dinámica**: Usa variables de entorno para la URL de conexión
3. **Metadatos SQLModel**: Utiliza `SQLModel.metadata` para auto-generación

### Comandos Básicos de Migración

#### 1. Crear una Nueva Migración

```bash
# Generar migración automáticamente basada en cambios de modelos
alembic revision --autogenerate -m "descripción del cambio"
```

#### 2. Aplicar Migraciones

```bash
# Aplicar la última migración
alembic upgrade head

# Aplicar migración específica
alembic upgrade [revision_id]

# Aplicar siguiente migración
alembic upgrade +1
```

#### 3. Revertir Migraciones

```bash
# Revertir a migración anterior
alembic downgrade -1

# Revertir a migración específica
alembic downgrade [revision_id]

# Revertir todo (¡CUIDADO!)
alembic downgrade base
```

#### 4. Ver Estado de Migraciones

```bash
# Ver historial de migraciones
alembic history

# Ver migración actual
alembic current

# Ver migraciones pendientes
alembic show head
```

### Ejemplo de Flujo de Trabajo

1. **Modificar un modelo existente:**

   ```python
   # En app/users/infra/db/models.py
   class UserModel(UserBaseModel, table=True):
       # Agregar nuevo campo
       phone: Optional[str] = Field(default=None)
   ```

2. **Generar la migración:**

   ```bash
   alembic revision --autogenerate -m "add phone field to user model"
   ```

3. **Revisar el archivo generado:**

   ```python
   # migrations/versions/[hash]_add_phone_field_to_user_model.py
   def upgrade() -> None:
       op.add_column('usermodel', sa.Column('phone', sa.VARCHAR(), nullable=True))

   def downgrade() -> None:
       op.drop_column('usermodel', 'phone')
   ```

4. **Aplicar la migración:**
   ```bash
   alembic upgrade head
   ```

## 💾 Gestión de Sesiones

### Configuración de Sesión

```python
# app/shared/infra/db/session.py
from sqlmodel import Session

def get_db():
    """Dependencia para obtener sesión de base de datos"""
    with Session(engine) as session:
        yield session
```

### Uso en FastAPI

```python
from fastapi import Depends
from sqlmodel import Session
from app.shared.infra.db.session import get_db

@app.post("/users/")
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Operaciones con la base de datos
    pass
```

## 🧪 Base de Datos para Pruebas

### Configuración de Pruebas

```python
# conftest.py
import pytest
from sqlmodel import Session, create_engine
from app.shared.infra.db.config import settings

@pytest.fixture
def db_session():
    engine = create_engine(settings.TEST_DATABASE_URL)
    with Session(engine) as session:
        yield session
```
