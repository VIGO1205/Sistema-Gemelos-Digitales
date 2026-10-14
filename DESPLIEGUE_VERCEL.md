# Despliegue gratuito para probar el gemelo digital

## Alternativa cuando Render no inicia las compilaciones: API y React en Vercel

Se pueden crear **dos proyectos de Vercel desde este mismo repositorio**. La base PostgreSQL permanece en Render; Vercel no aloja esa base directamente. Esta alternativa utiliza el mismo artefacto Random Forest y conserva el diseño del frontend. No requiere Web Service de Render.

1. En Vercel crea el proyecto de **API** desde el repositorio. Deja **Root Directory vacío** y selecciona **FastAPI**. No configures Build Command ni Output Directory. El archivo `server.py` es la entrada, `requirements.txt` instala solo dependencias de ejecución y `.vercelignore` excluye los archivos de entrenamiento.
2. En las variables de entorno del proyecto API configura `DATABASE_URL` con la **External Database URL** de Render PostgreSQL, cambiando `postgresql://` por `postgresql+asyncpg://` y añadiendo `?sslmode=require` si no está presente. Usa la URL externa, no la interna. Configura también `SECRET_KEY`, `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD`, `DEMO_ACCOUNTS_ENABLED=false`, `ENABLE_PUBLIC_REGISTRATION=false`, `DEBUG=false` y `CORS_ORIGINS` con la URL final del frontend. Nunca uses variables `VITE_` para secretos.
3. Despliega la API y comprueba `/health` y `/api/copper-creek/model-info` en su dominio Vercel. La segunda ruta debe indicar `Random Forest`.
4. Crea el proyecto de **frontend** desde el mismo repositorio, con **Root Directory `frontend`** y preset **Vite**. Configura `VITE_API_BASE_URL` con el dominio HTTPS de la API, sin barra final. Despliega y prueba el inicio de sesión y el visor 3D.
5. Si todavía no conoces el dominio final del frontend, usa temporalmente `CORS_ORIGINS=http://localhost:3000` al desplegar la API y actualízala al dominio Vercel antes de probar el navegador.

El proyecto FastAPI se empaqueta como una sola Vercel Function: el límite estándar de Python es 500 MB sin comprimir, con 2 GB de memoria en Hobby. Hay que confirmar en el primer despliegue que las dependencias y el modelo caben. La respuesta JSON de la escena ronda 2.7 MB y está por debajo del límite de 4.5 MB por respuesta. La conexión externa de Render PostgreSQL usa TLS y puede tener más latencia que la conexión interna.

## Variante original: API en Render, React en Vercel

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

   `INITIAL_ADMIN_EMAIL` y `INITIAL_ADMIN_PASSWORD` crean la cuenta administradora si ese correo aún no existe, incluso cuando la base ya contiene otros usuarios. No se envían al frontend ni rellenan el formulario de inicio de sesión. Si la cuenta ya existe, cambiar esas variables no modifica su contraseña. El login no muestra cuentas ni contraseñas de demostración.

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
