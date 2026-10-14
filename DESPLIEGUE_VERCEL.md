# Despliegue del frontend en Vercel

El proyecto tiene tres servicios de ejecución: React/Vite, FastAPI y el motor de inferencia, además de PostgreSQL. Vercel publica el **frontend**. La API, el motor y la base de datos necesitan un alojamiento público aparte; sin ellos, la página de inicio de sesión y las vistas de datos no pueden funcionar.

## 1. Publicar la API y el motor

Despliega `backend/`, `motor_ia_m6/` y PostgreSQL en un servidor que admita procesos persistentes o contenedores. El motor necesita los archivos de `motor_ia_m6/model_artifacts/`; el backend necesita `backend/data/copper_creek_mammoth.json`. En el backend configura `ML_INFERENCE_URL` con la dirección interna del motor.

Antes de exponer la API a Internet, configura en su entorno:

- `DATABASE_URL` y `DATABASE_URL_SYNC`: conexiones a PostgreSQL.
- `SECRET_KEY`: valor nuevo, aleatorio y privado para los tokens.
- `CORS_ORIGINS`: URL exacta del frontend de Vercel, con `https://` y sin barra final. Si hay dominio propio o previsualizaciones, agrega cada origen permitido separado por comas.
- `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD`: credenciales privadas para crear el primer administrador en una base de datos vacía. Cambiar estas variables posteriormente **no cambia** una cuenta ya creada.
- `DEMO_ACCOUNTS_ENABLED=false` y `ENABLE_PUBLIC_REGISTRATION=false`.
- `DEBUG=false`.

No reutilices las contraseñas de demostración. El archivo `backend/.env` local está excluido de Git.

El `docker-compose.prod.yml` exige contraseña de PostgreSQL, clave de sesión y orígenes CORS en el entorno. Es un punto de partida para alojar los servicios; revisa red, TLS, respaldo de la base de datos y acceso administrativo en tu proveedor antes de abrirlos al público.

## 2. Importar en Vercel

1. En Vercel, importa el repositorio de GitHub.
2. Selecciona **Root Directory: `frontend`** y **Framework Preset: Vite**.
3. Usa `npm run build` como comando de compilación y `dist` como directorio de salida. La versión de Node debe ser compatible con las dependencias del proyecto (Node 20 o posterior).
4. En **Environment Variables**, agrega `VITE_API_BASE_URL=https://tu-api.example.com` (URL pública real de FastAPI, sin barra final). Configúrala para Production y Preview según corresponda.
5. Despliega. Comprueba el inicio de sesión, `GET /health` de la API, el visor 3D y la consulta de ley.

`VITE_API_BASE_URL` es una dirección visible en el navegador, nunca una credencial. Vercel la incorpora al bundle al compilar: si cambia, vuelve a desplegar. `frontend/vercel.json` envía las rutas de la aplicación React a `index.html`; las llamadas a `/api` van al origen indicado en `VITE_API_BASE_URL`.

Para desarrollo local, `docker-compose.yml` conserva las cuentas de demostración y el proxy de Vite. El despliegue de producción no las activa.
