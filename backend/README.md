# M-6 Gemelo Digital — Backend API (FastAPI + PostgreSQL)

Backend RESTful para la plataforma de Gemelo Digital M-6, implementado con **FastAPI**, **SQLAlchemy 2.0 (async)**, **Alembic** y **PostgreSQL**.

## 🏗 Arquitectura

```
backend/
├── app/
│   ├── main.py              # Punto de entrada FastAPI
│   ├── config.py            # Configuración Pydantic Settings
│   ├── database.py          # Engine + Session async + Base
│   ├── seeders.py           # Datos iniciales (mocks → PostgreSQL)
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # API endpoints (CRUD + Bayesiano)
│   └── services/            # Lógica de negocio (motor bayesiano)
├── alembic/                 # Migraciones de base de datos
├── requirements.txt
├── Dockerfile
└── .env
```

## 🚀 Cómo ejecutar

### Opción A: Docker Compose (Recomendado)

Desde la raíz del proyecto:

```bash
docker-compose up --build
```

Esto levanta:
- **PostgreSQL** en `localhost:5432`
- **Backend FastAPI** en `http://localhost:8000`
- **Frontend React** en `http://localhost:3000`

### Opción B: Manual (desarrollo local)

1. **Crear base de datos PostgreSQL:**
```bash
createdb m6_gemelo_digital
```

2. **Instalar dependencias:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configurar variables de entorno:**
Crear `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/m6_gemelo_digital
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/m6_gemelo_digital
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DEBUG=True
```

4. **Ejecutar migraciones (opcional):**
```bash
cd backend
alembic upgrade head
```

5. **Iniciar servidor:**
```bash
uvicorn app.main:app --reload --port 8000
```

6. **Documentación interactiva:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📡 Endpoints principales

| Recurso | Endpoint | Descripción |
|---------|----------|-------------|
| Proyectos | `GET /api/projects` | Listar proyectos mineros |
| Bloques | `GET /api/blocks` | Listar modelo de bloques (filtros por banco, ley, incertidumbre) |
| Sondajes | `GET /api/drillholes` | Listar sondajes con sus muestras |
| Alertas | `GET /api/alerts` | Alertas operacionales |
| Bayesiano | `POST /api/bayesian/inference/{block_id}` | Inferencia variacional MC por bloque |
| Reconciliación | `GET /api/bayesian/reconciliation` | Reconciliación banco: Kriging vs Bayesiano |
| Reportes | `GET /api/reports/excel` | Exportar Excel del modelo de bloques |
| Auditoría | `GET /api/audit-logs` | Logs de auditoría RBAC |
| SPC | `GET /api/process-control` | Datos EWMA/CUSUM |
| Health | `GET /health` | Check de salud |

## 🧪 Tests

```bash
cd backend
pytest
```

## 🗄 Modelo de datos

Entidades principales:
- **projects**: Proyectos mineros
- **blocks**: Modelo de bloques 3D con leyes e incertidumbres
- **drillholes / drillhole_samples**: Sondajes y sus intervalos
- **hyperspectral_signatures**: Firmas espectrales VNIR/SWIR
- **alerts**: Alertas operacionales
- **audit_logs**: Trazabilidad de acciones
- **process_control_points**: Datos SPC (EWMA/CUSUM)
- **training_loss_history**: Historial de entrenamiento ELBO
