# 🚀 Proyecto con uv y FastAPI

Este proyecto utiliza **uv** para la gestión de dependencias y entorno, junto con **FastAPI** para el desarrollo del servidor.

---

## ⚙️ Herramientas de Desarrollo

### 📦 uv

**uv** es la herramienta principal del proyecto. NO usar `pip`. Consulta la [documentación oficial](https://docs.astral.sh/uv/#installation).

#### Comandos básicos:
- Instalar dependencias: `uv sync`
- Agregar dependencias: `uv add fastapi --standard`
- Ejecutar scripts: `uv run <comando>`
  - Servidor con reload (solo código; evita vigilar `.venv` en Windows/OneDrive):
    `uv run uvicorn app.main:app --reload --reload-dir app --reload-dir agent`
- Shortcut para el servidor: `uv run fastapi dev` (si ves reload infinito por `WatchFiles` en `.venv`, usa el comando `uvicorn` de arriba)

---

### 🧹 Ruff

Usa **Ruff** para linting. Instala la extensión en **VSCode**.

---

### 🔍 Type Checking

El proyecto usa tipado estándar. Actívalo en **VSCode**.

---

## 🛠️ Configuración

1. Instala dependencias:
   ```bash
   uv sync
   ```

2. Corre el servidor en desarrollo:
   ```bash
   uv run uvicorn app.main:app --reload --reload-dir app --reload-dir agent
   ```

---

## 📚 Recursos

- [Documentación de uv](https://docs.astral.sh/uv/#installation)
- [Documentación de FastAPI](https://fastapi.tiangolo.com/)
- [Ruff en GitHub](https://github.com/charliermarsh/ruff)
