import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import engine, Base, async_session
from app.routers import projects, blocks, drillholes, alerts, bayesian, reports, audit_logs, process_control, hyperspectral, auth, chat, reconciliation, economics, drillhole_planning, active_models, models_serving, dispatch, copper_creek
from app.seeders import seed_database

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed data if needed
    async with async_session() as db:
        await seed_database(db)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST para el Gemelo Digital M-6: control de leyes mineras con cuantificación de incertidumbre bayesiana.",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(projects.router, prefix="/api/projects", tags=["Proyectos"])
app.include_router(blocks.router, prefix="/api/blocks", tags=["Bloques"])
app.include_router(drillholes.router, prefix="/api/drillholes", tags=["Sondajes"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alertas"])
app.include_router(bayesian.router, prefix="/api/bayesian", tags=["Motor Bayesiano"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reportes"])
app.include_router(audit_logs.router, prefix="/api/audit-logs", tags=["Auditoría"])
app.include_router(process_control.router, prefix="/api/process-control", tags=["Control de Procesos"])
app.include_router(hyperspectral.router, prefix="/api/hyperspectral", tags=["Hiperespectral"])
app.include_router(chat.router, tags=["Chat IA"])
app.include_router(reconciliation.router, tags=["Reconciliación"])
app.include_router(active_models.router, tags=["Modelos Activos"])
app.include_router(models_serving.router, tags=["Inferencia Motor IA"])
app.include_router(dispatch.router, tags=["Despacho de Contramedidas"])
app.include_router(economics.router, tags=["Análisis Económico"])
app.include_router(drillhole_planning.router, tags=["Planificación de Sondajes"])
app.include_router(copper_creek.router)


@app.get("/health", tags=["Sistema"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# Serve static files in production (if dist folder exists)
static_dir = os.path.join(os.path.dirname(__file__), "../static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"detail": "Not found"}
