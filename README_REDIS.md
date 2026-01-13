# Redis para Agente de Timesheets

## 🎯 ¿Qué se implementó?

Se reemplazó `InMemorySaver` por **Redis con TTL automático** para evitar fugas de memoria.

**Problema anterior:**
- ❌ Conversaciones nunca se eliminaban
- ❌ Memoria crecía indefinidamente

**Solución actual:**
- ✅ Redis con TTL de 2 horas (auto-limpieza)
- ✅ Endpoint DELETE para limpieza manual
- ✅ Escalable a múltiples instancias

---

## 🚀 Setup Rápido

### Desarrollo Local

```powershell
# Windows
.\setup_redis.ps1

# Linux/Mac
chmod +x setup_redis.sh && ./setup_redis.sh
```

Esto instala y configura Redis en Docker automáticamente.

### Producción en Railway

**Paso 1:** Agregar Redis
```
Railway Dashboard → + New → Database → Add Redis
```

**Paso 2:** Configurar variables en tu servicio FastAPI
```bash
REDIS_HOST=${{Redis.REDISHOST}}
REDIS_PORT=${{Redis.REDISPORT}}
REDIS_PASSWORD=${{Redis.REDISPASSWORD}}
REDIS_DB=0
REDIS_TTL_HOURS=2
REDIS_MAX_CONNECTIONS=10
```

**Paso 3:** Deploy (automático)

**Costo estimado:** ~$1 USD/mes

---

## 📁 Archivos Modificados

### Nuevos
```
agent/infra/redis_client.py         # Pool de conexiones
agent/infra/redis_checkpointer.py   # Checkpointer con TTL
docker-compose.yml                   # Redis para desarrollo
```

### Modificados
```
pyproject.toml          # + redis>=5.0.0
agent/core/agent.py     # Usa RedisCheckpointer
agent/services/cargar_horas.py  # Expone delete_conversation()
agent/api/routers.py    # + DELETE /agent/conversation/{id}
```

---

## 🔌 Nuevo Endpoint (Frontend)

```http
DELETE /agent/conversation/{conversation_id}
Authorization: Bearer {token}
```

**El frontend DEBE llamar este endpoint cuando el usuario cierra el diálogo.**

### Ejemplo JavaScript

```javascript
// Al abrir el diálogo
const conversationId = crypto.randomUUID();

// Al cerrar el diálogo
async function handleClose() {
  await fetch(`/agent/conversation/${conversationId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
}
```

---

## ⚙️ Variables de Entorno

### Desarrollo Local (.env)
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_TTL_HOURS=2
REDIS_MAX_CONNECTIONS=10
```

### Railway (usa referencias)
```bash
REDIS_HOST=${{Redis.REDISHOST}}
REDIS_PORT=${{Redis.REDISPORT}}
REDIS_PASSWORD=${{Redis.REDISPASSWORD}}
REDIS_DB=0
REDIS_TTL_HOURS=2
REDIS_MAX_CONNECTIONS=10
```

## 🧪 Verificación

### Local
```bash
# Verificar Redis
docker compose ps
redis-cli ping  # → PONG

# Ver conversaciones activas
redis-cli keys "langgraph:checkpoint:*"
```

### Railway
Verificar en logs del servicio FastAPI:
```
✅ Redis connected successfully at redis.railway.internal:6379
```

---

## 🛠️ Troubleshooting

### Redis no conecta (Local)
```bash
docker compose up -d redis
docker compose logs redis
```

### Redis no conecta (Railway)
- Verificar que las variables usan referencias: `${{Redis.REDISHOST}}`
- Verificar que Redis está corriendo (check verde en Dashboard)

### Limpiar todas las conversaciones
```bash
redis-cli FLUSHDB
```

---

## 💰 Costos

### Desarrollo
- **Local (Docker):** Gratis

### Railway
- **Redis:** ~$0.50-1.00 USD/mes
- **Plan Hobby:** $5 gratis/mes (suficiente)
- **Plan Pro:** $20/mes con $20 crédito

---

## 📊 Arquitectura

```
Frontend
  ↓ POST /agent/cargar-horas-agent
  ↓ DELETE /agent/conversation/{id}
FastAPI (agent/api/routers.py)
  ↓
Agent Service (agent/services/cargar_horas.py)
  ↓
RedisCheckpointer (agent/infra/redis_checkpointer.py)
  ↓
Redis
  → TTL: 2 horas
  → Auto-limpieza
```

---

## ✅ Checklist

### Backend
- [x] Redis client implementado
- [x] Checkpointer con TTL
- [x] Endpoint DELETE
- [x] Soporta Railway y local

### Por hacer
- [ ] Instalar Redis (ejecutar setup script)
- [ ] Modificar frontend para llamar DELETE
- [ ] Probar flujo completo
- [ ] Deploy a Railway

---

## 🆘 Soporte

### Ver conversaciones activas
```bash
redis-cli keys "langgraph:checkpoint:*" | wc -l
```

### Ver memoria usada
```bash
redis-cli info memory | grep used_memory_human
```

### Ver TTL de una conversación
```bash
redis-cli ttl "langgraph:checkpoint:tu-conversation-id:checkpoint-id"
```

---

**Implementación completada.** Ejecuta el script de setup y ya puedes usar Redis.

