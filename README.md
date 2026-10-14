<div align="center">
<h1>M-6 Gemelo Digital</h1>
<p><strong>Plataforma de Gemelo Digital para control de leyes de mineral en minería a cielo abierto</strong></p>
<p>Fusión de modelos de bloques, análisis de muestras de barrenos e imágenes hiperespectrales mediante aprendizaje profundo bayesiano.</p>
</div>

Para publicar el frontend en Vercel y conectar los servicios necesarios, consulta [DESPLIEGUE_VERCEL.md](DESPLIEGUE_VERCEL.md).

---

## Alcance actual de la demostración académica

El frontend reúne tres contextos de datos distintos. Las pantallas no representan un único yacimiento conectado de extremo a extremo:

| Vista | Datos y cálculo | Límite |
| --- | --- | --- |
| Gemelo Digital 3D | Sondajes públicos de Copper Creek; ley estimada con el Random Forest publicado, IDW3 de referencia y tajo Mammoth aproximado | Exploración visual; no es el modelo de bloques oficial ni valida recursos, reservas o despacho |
| Dashboard, alertas, reconciliación, economía y Motor informativo | Mismos cubos y modelo publicado de Copper Creek en sus componentes originales | Sin datos de planta, despacho, tonelaje validado ni valoración económica del proyecto |
| Geoespacial, planificador y reportes | Mina Esperanza Sur, escenario generado en PostgreSQL | Simulación académica independiente de Copper Creek |
| Sondajes GeoMet | Experimento independiente con modelo publicado por el Motor IA | Predice Cu de puntos X/Y/Z del conjunto GeoMet; no alimenta automáticamente el visor Copper Creek |

El planificador calcula escenarios de nuevos sondajes sin crear ensayos ni cambiar la base de datos. Los reportes exportados son académicos y no llevan certificación JORC/NI 43-101 ni firma de una persona competente. Para la procedencia y los supuestos de la escena 3D, consulta [backend/data/README.md](backend/data/README.md).

Comprobaciones locales: `cd frontend && npm run lint && npm run build`; `GET /health` en FastAPI. Las integraciones externas, como webhooks de despacho, requieren configuración propia.

---

## 🏗 Arquitectura Full Stack

```
┌─────────────────┐      HTTP/REST       ┌──────────────────┐      SQL       ┌─────────────────┐
│   React 19      │ ◄──────────────────► │  FastAPI (Python)│ ◄────────────► │  PostgreSQL 15+ │
│   (Frontend)    │    Axios/Fetch       │  Uvicorn + ASGI  │   SQLAlchemy   │  PostGIS ext.   │
└─────────────────┘                      └──────────────────┘                └─────────────────┘
```

### Tecnologías

- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS + Three.js + Recharts
- **Backend**: FastAPI + SQLAlchemy 2.0 (async) + Alembic + Uvicorn
- **Base de datos**: PostgreSQL 15+ (con extensión PostGIS opcional)
- **Contenedores**: Docker + Docker Compose

---

## 🚀 Cómo ejecutar el proyecto completo

### Opción 1: Docker Compose (Recomendado)

Levanta toda la arquitectura con un solo comando:

```bash
docker-compose up --build
```

Servicios disponibles:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Base de datos PostgreSQL**: localhost:5432

### Opción 2: Manual (desarrollo local)

#### 1. Base de datos PostgreSQL

```bash
# Crear base de datos
createdb m6_gemelo_digital

# O con Docker:
docker run -d --name m6_postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=m6_gemelo_digital -p 5432:5432 postgres:15-alpine
```

#### 2. Backend (FastAPI)

```bash
cd backend

# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate
# Activar (Linux/Mac)
# source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
uvicorn app.main:app --reload --port 8000
```

El backend seederá automáticamente los datos iniciales al primer arranque.

#### 3. Frontend (React)

```bash
cd frontend
npm install

# Crear .env.local con:
# GEMINI_API_KEY=tu-api-key
# VITE_API_BASE_URL=http://localhost:8000

npm run dev
```

El frontend estará disponible en http://localhost:3000

---

## 📂 Estructura del proyecto

```
Sistema-Gemelos-Digitales/
├── frontend/                    # React 19 + Vite
│   ├── src/
│   │   ├── components/          # Componentes UI (14 módulos)
│   │   ├── context/             # Contextos React (Auth, Theme, Data)
│   │   ├── services/            # Clientes API y motores
│   │   ├── types/               # Tipos TypeScript
│   │   └── mock/                # Datos mock (fallback offline)
│   ├── package.json
│   ├── vite.config.ts
│   ├── Dockerfile               # Desarrollo (Node + Vite)
│   └── Dockerfile.prod          # Producción (Nginx)
│
├── backend/                     # FastAPI + PostgreSQL
│   ├── app/
│   │   ├── main.py              # Punto de entrada FastAPI
│   │   ├── config.py            # Pydantic Settings
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── seeders.py           # Datos iniciales
│   │   ├── models/              # SQLAlchemy ORM
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── routers/             # API endpoints
│   │   └── services/            # Motor bayesiano Python
│   ├── alembic/                 # Migraciones
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
│
├── motor_ia_m6/                 # Motor de ML (Streamlit)
│   ├── app.py                   # Aplicación Streamlit (6 fases CRISP-DM)
│   ├── training/                # Pipeline de entrenamiento
│   ├── models/                  # 5 modelos predictivos
│   ├── evaluation/              # Métricas avanzadas
│   ├── data/                    # Generador sintético
│   ├── database/                # Schema PostgreSQL
│   └── requirements.txt
│
├── docker-compose.yml           # Orquestación desarrollo
├── docker-compose.prod.yml      # Orquestación producción
└── README.md
```

---

## 📡 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/projects` | Listar proyectos mineros |
| `GET` | `/api/projects/{id}` | Detalle de proyecto |
| `GET` | `/api/blocks` | Listar bloques (filtros: banco, ley, incertidumbre, categoría) |
| `GET` | `/api/blocks/{id}` | Detalle de bloque |
| `GET` | `/api/drillholes` | Listar sondajes con muestras |
| `GET` | `/api/drillholes/{id}` | Detalle de sondaje |
| `GET` | `/api/alerts` | Alertas operacionales |
| `PATCH` | `/api/alerts/{id}/acknowledge` | Reconocer alerta |
| `POST` | `/api/bayesian/inference/{block_id}` | Inferencia variacional MC por bloque |
| `GET` | `/api/bayesian/reconciliation` | Reconciliación Kriging vs Bayesiano |
| `GET` | `/api/reports/excel` | Exportar modelo de bloques a Excel |
| `GET` | `/api/reports/summary` | Resumen ejecutivo con métricas JORC |
| `GET` | `/api/audit-logs` | Logs de auditoría RBAC |
| `GET` | `/api/process-control` | Datos SPC EWMA/CUSUM |
| `GET` | `/health` | Health check |

---

## 🧠 Motor Bayesiano

El backend implementa el motor de inferencia bayesiana en Python:

- **Kernel Matérn 5/2** para covarianza espacial
- **Simulación Monte Carlo** con transformada Box-Muller
- **Descomposición de incertidumbre**:
  - Epistémica (falta de datos) → reducible
  - Aleatoria (variabilidad natural) → irreducible
- **Percentiles P10-P50-P90** para intervalos de credibilidad
- **Reconciliación de banco** comparando modelo base vs gemelo digital

---

## 🗄 Modelo de datos (PostgreSQL)

Entidades principales:
- **projects**: Proyectos mineros (Esperanza Sur, Centinela Norte, Quebrada Blanca)
- **blocks**: ~500+ bloques 3D con coordenadas, leyes Cu/Au, incertidumbres epistémicas/aleatorias, categorías JORC
- **drillholes / drillhole_samples**: Sondajes DDH, RC y blastholes con intervalos de ley
- **hyperspectral_signatures**: Firmas espectrales VNIR/SWIR (Illita, Biotita, Clorita, Crisocola)
- **alerts**: Alertas de alta incertidumbre, desviación de ley, riesgo de dilución
- **audit_logs**: Trazabilidad completa de acciones (QP/Geólogo/Planificación/Supervisor)
- **process_control_points**: Datos de control estadístico de procesos (EWMA/CUSUM)
- **training_loss_history**: Convergencia ELBO del entrenamiento bayesiano

---

## ✅ Testing

```bash
# Backend tests
cd backend
pytest

# Frontend lint
npm run lint
```

---

## 📄 Licencia & Estándares

- Conforme a **JORC 2012** / **NI 43-101**
- Sistema de coordenadas: **EPSG:32719** (WGS 84 / UTM Zone 19S)
- Datum para operaciones en Chile (Región de Antofagasta / Tarapacá)
