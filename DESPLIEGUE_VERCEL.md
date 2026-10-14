# Despliegue gratuito para probar el gemelo digital

La variante de Render ejecuta **FastAPI y el Random Forest publicado de Copper Creek en un solo Web Service**. No requiere crear un Private Service ni desplegar Streamlit. React se publica en Vercel y PostgreSQL se mantiene en Render. El Dockerfile local y el motor separado siguen disponibles para desarrollo.

## 1. Crear el Web Service de FastAPI en Render

1. En Render, elige **New > Web Service** y conecta `VIGO1205/Sistema-Gemelos-Digitales`.
2. Elige **Language: Docker**, **Instance type: Free** y la **misma región** del PostgreSQL que ya creaste.
3. Deja **Root Directory vacío** (raíz del repositorio). Configura **Dockerfile Path: `backend/Dockerfile.render`**. El contexto de Docker debe ser la raíz del repositorio.
4. En Environment agrega:

   | Variable | Valor |
   | --- | --- |
   | `DATABASE_URL` | URL **interna** de Render PostgreSQL, cambiando solamente `postgresql://` por `postgresql+asyncpg://` |
   | `SECRET_KEY` | Cadena aleatoria, larga y privada para firmar sesiones |
   | `INITIAL_ADMIN_EMAIL` | Tu correo para el primer administrador |
   | `INITIAL_ADMIN_PASSWORD` | Contraseña privada y fuerte para ese administrador |
   | `CORS_ORIGINS` | Por ahora `http://localhost:3000`; actualízala con el dominio Vercel exacto después |
   | `DEMO_ACCOUNTS_ENABLED` | `false` |
   | `ENABLE_PUBLIC_REGISTRATION` | `false` |
   | `DEBUG` | `false` |

   `COPPER_CREEK_LOCAL_MODEL=true` ya viene en la imagen. **No agregues `ML_INFERENCE_URL`** para esta variante. `DATABASE_URL_SYNC` solo se necesita si ejecutarás Alembic; el arranque normal crea las tablas mediante SQLAlchemy asíncrono. Guarda las credenciales únicamente en Render, nunca en GitHub ni en el chat.

5. Crea el Web Service. Cuando Render termine, comprueba `https://TU-SERVICIO.onrender.com/health` y `https://TU-SERVICIO.onrender.com/api/copper-creek/model-info`. El primero debe responder `status: ok` y el segundo debe mostrar `model_name: Random Forest`.

La imagen verifica durante la construcción que el modelo guardado se puede cargar con las versiones de librerías de sus metadatos. Si falla ese paso, revisa el registro de construcción antes de configurar Vercel. El visor 3D y la consulta de ley usan `/api/copper-creek/predict` en este mismo servicio. Entrenar otro modelo en Streamlit no modifica esta imagen: habría que publicar el nuevo artefacto y desplegar otra versión.

## 2. Publicar React en Vercel

1. Importa el mismo repositorio. Selecciona **Root Directory: `frontend`** y **Framework Preset: Vite**.
2. Usa `npm run build` y directorio de salida `dist`. Usa Node 20 o posterior.
3. En Environment Variables, añade `VITE_API_BASE_URL=https://TU-SERVICIO.onrender.com` sin barra final.
4. Despliega. Copia la URL final de Vercel y cambia `CORS_ORIGINS` en Render a esa URL exacta, por ejemplo `https://mi-gemelo.vercel.app`. Guarda y espera el nuevo despliegue de Render.
5. Prueba inicio de sesión, Dashboard Ejecutivo, Gemelo Digital 3D y una consulta de ley sobre un cubo.

`VITE_API_BASE_URL` es pública en el navegador; no pongas secretos en ella. Si cambia la URL de FastAPI, Vercel debe recompilar el frontend.

## Alcance del plan gratuito

El plan Free de Render puede suspender el Web Service tras 15 minutos sin tráfico; la primera visita siguiente tarda en arrancar. Tiene 512 MB de RAM, por lo que el modelo se carga bajo demanda y se conserva en memoria una vez cargado. **La capacidad real debe comprobarse con el primer despliegue**. Render indica que su PostgreSQL Free expira a los 30 días y no ofrece copias de seguridad; úsalo para pruebas académicas, no como almacenamiento permanente.

Las rutas heredadas del Motor IA y GeoMet que dependan del servicio separado no se trasladan automáticamente a esta variante. El alcance de esta imagen es la reconstrucción y el modelo ganador de **Copper Creek**. El `docker-compose.yml` local sigue utilizando el motor separado.
