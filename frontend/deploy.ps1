# M-6 Gemelo Digital - Script de Despliegue
# Uso: .\deploy.ps1 [-Environment dev|prod] [-Action up|down|build|logs]

param(
    [string]$Environment = "dev",
    [string]$Action = "up"
)

$composeFile = if ($Environment -eq "prod") { "docker-compose.prod.yml" } else { "docker-compose.yml" }

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  M-6 Gemelo Digital - Despliegue" -ForegroundColor Cyan
Write-Host "  Modo: $Environment | Accion: $Action" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

switch ($Action.ToLower()) {
    "up" {
        Write-Host "Levantando servicios..." -ForegroundColor Green
        docker-compose -f $composeFile up --build -d
        
        Write-Host ""
        Write-Host "Servicios desplegados:" -ForegroundColor Green
        if ($Environment -eq "dev") {
            Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Yellow
            Write-Host "  Backend API: http://localhost:8000" -ForegroundColor Yellow
            Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Yellow
            Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor Yellow
        } else {
            Write-Host "  Frontend: http://localhost" -ForegroundColor Yellow
            Write-Host "  Backend API: http://localhost:8000" -ForegroundColor Yellow
            Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor Yellow
        }
    }
    "down" {
        Write-Host "Deteniendo servicios..." -ForegroundColor Red
        docker-compose -f $composeFile down
    }
    "build" {
        Write-Host "Reconstruyendo imagenes..." -ForegroundColor Blue
        docker-compose -f $composeFile build --no-cache
    }
    "logs" {
        Write-Host "Mostrando logs..." -ForegroundColor Magenta
        docker-compose -f $composeFile logs -f
    }
    "status" {
        Write-Host "Estado de los contenedores:" -ForegroundColor Blue
        docker-compose -f $composeFile ps
    }
    default {
        Write-Host "Accion no reconocida. Usa: up, down, build, logs, status" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
