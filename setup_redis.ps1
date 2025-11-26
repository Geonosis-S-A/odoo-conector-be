# Script de instalacion rapida de Redis para Windows PowerShell
# Este script configura todo lo necesario para usar Redis con el agente

Write-Host "Configurando Redis para el Agente de Timesheets" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar si Docker esta instalado
Write-Host "Verificando Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "OK - Docker esta instalado: $dockerVersion" -ForegroundColor Green
}
catch {
    Write-Host "ERROR - Docker no esta instalado. Por favor instala Docker Desktop primero." -ForegroundColor Red
    Write-Host "   Visita: https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 2. Verificar si Docker Compose esta disponible
Write-Host "Verificando Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker compose version
    Write-Host "OK - Docker Compose esta disponible: $composeVersion" -ForegroundColor Green
}
catch {
    Write-Host "ERROR - Docker Compose no esta disponible." -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. Crear archivo .env si no existe
Write-Host "Configurando variables de entorno..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    $envContent = @"
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_TTL_HOURS=2
REDIS_MAX_CONNECTIONS=10
"@
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "OK - Archivo .env creado" -ForegroundColor Green
}
else {
    Write-Host "INFO - Archivo .env ya existe, verificando variables de Redis..." -ForegroundColor Cyan
    
    # Verificar si existen variables de Redis
    $envContent = Get-Content ".env" -Raw -ErrorAction SilentlyContinue
    if ($envContent -notmatch "REDIS_HOST") {
        $redisVars = @"

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_TTL_HOURS=2
REDIS_MAX_CONNECTIONS=10
"@
        Add-Content -Path ".env" -Value $redisVars -Encoding UTF8
        Write-Host "OK - Variables de Redis agregadas a .env" -ForegroundColor Green
    }
    else {
        Write-Host "OK - Variables de Redis ya estan configuradas" -ForegroundColor Green
    }
}
Write-Host ""

# 4. Instalar dependencias Python
Write-Host "Instalando dependencias Python..." -ForegroundColor Yellow
try {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "   Usando uv..." -ForegroundColor Cyan
        uv sync
    }
    else {
        Write-Host "   Usando pip..." -ForegroundColor Cyan
        pip install "redis>=5.0.0"
    }
    Write-Host "OK - Dependencias instaladas" -ForegroundColor Green
}
catch {
    Write-Host "ADVERTENCIA - Error instalando dependencias: $_" -ForegroundColor Yellow
}
Write-Host ""

# 5. Iniciar Redis con Docker Compose
Write-Host "Iniciando Redis con Docker Compose..." -ForegroundColor Yellow
try {
    docker compose up -d redis
    Write-Host "OK - Redis iniciado" -ForegroundColor Green
}
catch {
    Write-Host "ERROR - Error iniciando Redis: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 6. Esperar a que Redis este listo
Write-Host "Esperando a que Redis este listo..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 7. Verificar conexion a Redis
Write-Host "Verificando conexion a Redis..." -ForegroundColor Yellow
try {
    $ping = docker exec odoo-connector-redis redis-cli ping 2>$null
    if ($ping -eq "PONG") {
        Write-Host "OK - Redis esta funcionando correctamente" -ForegroundColor Green
    }
    else {
        Write-Host "ADVERTENCIA - Respuesta inesperada de Redis: $ping" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "ADVERTENCIA - No se pudo conectar a Redis. Mostrando logs..." -ForegroundColor Yellow
    docker compose logs redis
}
Write-Host ""

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Configuracion completada!" -ForegroundColor Green
Write-Host ""
Write-Host "Proximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Verifica que Redis esta corriendo: docker compose ps"
Write-Host "   2. Inicia tu aplicacion FastAPI"
Write-Host "   3. Prueba el agente de timesheets"
Write-Host ""
Write-Host "Para mas informacion, consulta:" -ForegroundColor Cyan
Write-Host "   - README_REDIS.md"
Write-Host ""
Write-Host "Si tienes problemas:" -ForegroundColor Yellow
Write-Host "   - Ver logs: docker compose logs redis"
Write-Host "   - Reiniciar: docker compose restart redis"
Write-Host "   - Detener: docker compose down"
Write-Host ""
