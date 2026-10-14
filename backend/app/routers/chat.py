import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import get_settings
from app.database import get_db
from app.auth import get_current_active_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage

router = APIRouter(prefix="/api/chat", tags=["Chat IA"])
settings = get_settings()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def build_system_prompt(ctx) -> str:
    """Construye el system prompt dinámico con contexto geológico."""
    lines = [
        "Eres el Copiloto IA Geológico del Gemelo Digital M-6, un asistente experto en geoestadística, control de leyes y minería de pórfidos cupríferos.",
        "",
        "CONTEXTO ACTUAL DEL PROYECTO:",
    ]

    if ctx.project_name:
        lines.append(f"• Faena: {ctx.project_name} — Yacimiento Pórfido Cu-Mo (Low-Grade, High-Tonnage)")
    if ctx.active_bench is not None:
        lines.append(f"• Banco activo: Z = {ctx.active_bench}m")
    if ctx.selected_block_id:
        block_info = f"• Bloque seleccionado: {ctx.selected_block_id}"
        if ctx.selected_block_cu is not None:
            block_info += f" — Ley Cu: {ctx.selected_block_cu:.2f}%"
        if ctx.selected_block_lithology:
            block_info += f" — Litología: {ctx.selected_block_lithology}"
        lines.append(block_info)
    if ctx.avg_bench_grade is not None:
        lines.append(f"• Ley promedio del banco: {ctx.avg_bench_grade:.2f}% Cu")
    if ctx.total_bench_tonnage is not None:
        lines.append(f"• Tonelaje total del banco: {ctx.total_bench_tonnage:,.0f} t")
    if ctx.cut_off_grade is not None:
        lines.append(f"• Cut-off grade: {ctx.cut_off_grade:.2f}%")
    if ctx.user_role:
        lines.append(f"• Usuario: {ctx.user_name or 'Desconocido'} | Rol: {ctx.user_role}")

    lines.extend([
        "",
        "ALCANCE DE LOS DATOS: Mina Esperanza Sur y sus bancos son un escenario generado para demostración. El visor 3D y el dashboard principal usan una reconstrucción exploratoria y aproximada de Copper Creek basada en sondajes públicos y un estimador elegido por validación entre IDW3, Random Forest y XGBoost. GeoMet es un experimento separado. No atribuyas datos sintéticos de planta, tonelaje o categorías internas a Copper Creek ni afirmes cumplimiento JORC/NI 43-101.",
        "MÓDULOS DEL SISTEMA M-6 (sidebar):",
        "1. Dashboard Ejecutivo — KPIs y gráficos SPC ilustrativos de Mina Esperanza Sur.",
        "2. Gemelo Digital 3D — Visor WebGL de Copper Creek con ley Cu exploratoria del estimador seleccionado y geometría aproximada.",
        "3. Motor Bayesiano & XAI — Descomposición de incertidumbre epistémica/aleatoria, simulador Monte Carlo.",
        "4. Gestión Geoespacial & SWIR — Sondajes, firmas hiperespectrales, alteración potásica/fílica.",
        "5. Alertas & Despacho — Notificaciones de variabilidad, riesgo de dilución, drift de calibración.",
        "6. Reconciliación Mine-to-Mill — Comparación simulada modelo vs puntos de planta generados.",
        "7. Análisis Económico — Escenario de valoración y costos supuestos; no calcula NPV.",
        "8. Planificador de Sondajes — Priorización ilustrativa por incertidumbre y distancia.",
        "9. Reportes académicos — Exportación PDF/Excel de datos simulados, sin firma QP ni certificación.",
        "10. Seguridad RBAC — Matriz de permisos por rol (ADMIN, SENIOR_GEOLOGIST, etc.).",
        "11. Arquitectura C4 — Diagramas del sistema, API REST, modelo ER.",
        "12. Copiloto IA (este chat) — Asistente flotante conectado a GROQ (qwen/qwen3.8-27b).",
        "",
        "ESTILO DE RESPUESTA:",
        "• Responde en español técnico-minero.",
        "• Usa datos del contexto cuando el usuario pregunte sobre el banco o bloque activo sin necesidad de que los repita.",
        "• Si pregunta sobre riesgo geoestadístico, distingue incertidumbre epistémica (modelo) vs aleatoria (datos).",
        "• Para recomendaciones de sondajes, trata las etiquetas Medido/Indicado/Inferido del ejemplo como reglas internas, no como clasificación JORC validada.",
        "• Mantén respuestas concisas (máx 3-4 párrafos) salvo que se solicite análisis profundo.",
        "• No inventes datos que no estén en el contexto; si no sabes algo, dilo claramente.",
    ])

    return "\n".join(lines)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Intentar responder mediante LangFlow si está habilitado
    if settings.USE_LANGFLOW and settings.LANGFLOW_FLOW_ID:
        try:
            langflow_endpoint = f"{settings.LANGFLOW_URL}/api/v1/run/{settings.LANGFLOW_FLOW_ID}?stream=false"
            last_user_message = request.messages[-1].content if request.messages else "Hola"

            # Usar session_id provisto por frontend o ID del usuario autenticado
            session_id = request.session_id or f"user_{current_user.id}"

            langflow_payload = {
                "input_value": last_user_message,
                "input_type": "chat",
                "output_type": "chat",
                "session_id": session_id,
                "tweaks": {}
            }

            headers = {
                "Content-Type": "application/json"
            }
            if settings.LANGFLOW_API_KEY:
                headers["x-api-key"] = settings.LANGFLOW_API_KEY
                headers["Authorization"] = f"Bearer {settings.LANGFLOW_API_KEY}"

            async with httpx.AsyncClient(timeout=60.0) as client:
                lf_response = await client.post(langflow_endpoint, json=langflow_payload, headers=headers)

            if lf_response.status_code == 200:
                lf_data = lf_response.json()
                assistant_text = ""

                # Extraer texto de la estructura de respuesta de LangFlow
                try:
                    outputs = lf_data.get("outputs", [])
                    if outputs:
                        sub_outputs = outputs[0].get("outputs", [])
                        if sub_outputs:
                            results = sub_outputs[0].get("results", {})
                            msg_obj = results.get("message", {})
                            if isinstance(msg_obj, dict):
                                if "data" in msg_obj and isinstance(msg_obj["data"], dict):
                                    assistant_text = msg_obj["data"].get("text", "")
                                if not assistant_text:
                                    assistant_text = msg_obj.get("text", "") or msg_obj.get("content", "")
                            elif isinstance(msg_obj, str):
                                assistant_text = msg_obj
                except Exception:
                    pass

                if not assistant_text and "result" in lf_data:
                    assistant_text = str(lf_data["result"])

                if assistant_text:
                    return ChatResponse(
                        message=ChatMessage(role="assistant", content=assistant_text),
                        model="LangFlow (Workflow M-6)",
                    )
        except Exception as e:
            # Fallback a GROQ directo si Langflow no está disponible
            pass

    # 2. Fallback / Motor Principal GROQ Directo
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de IA no está configurado. Falta GROQ_API_KEY o LangFlow no respondió.",
        )

    # Construir mensajes para GROQ
    groq_messages: List[dict] = []

    # System prompt con contexto geológico
    if request.context:
        system_prompt = build_system_prompt(request.context)
        groq_messages.append({"role": "system", "content": system_prompt})

    # Agregar historial de conversación (máx 10 mensajes para no exceder tokens)
    for msg in request.messages[-10:]:
        groq_messages.append({"role": msg.role, "content": msg.content})

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": groq_messages,
        "max_tokens": settings.GROQ_MAX_TOKENS,
        "temperature": settings.GROQ_TEMPERATURE,
    }

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(GROQ_API_URL, json=payload, headers=headers)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de conexión con GROQ: {str(exc)}",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error de GROQ: {response.status_code} — {response.text}",
        )

    data = response.json()
    try:
        assistant_msg = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Respuesta inesperada de GROQ: {str(exc)}",
        )

    return ChatResponse(
        message=ChatMessage(role="assistant", content=assistant_msg),
        model=settings.GROQ_MODEL,
    )

