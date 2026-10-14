"""
Router de Despacho Inmediato de Contramedidas.

Si se configura la variable de entorno DISPATCH_URL_<CANAL> (p.ej. una URL de
webhook.site, Slack, Teams o un endpoint SCADA), se envía un POST HTTP real con
la alerta y su contramedida recomendada. Sin URL configurada opera en modo
SIMULADO (demo), registrando igualmente la entrega en el audit log.
"""

import os
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_active_user
from app.database import get_db
from app.models import Alert, AuditLog, User

router = APIRouter(prefix="/api/dispatch", tags=["Despacho de Contramedidas"])

CHANNELS = {
    "DISPATCH_PALAS": {
        "label": "Pala / Dispatch",
        "role": "MINE_SUPERVISOR",
        "url_env": "DISPATCH_URL_PALAS",
    },
    "CONTROL_PLANTA_SART": {
        "label": "Planta Concentradora",
        "role": "PLANNING_ENGINEER",
        "url_env": "DISPATCH_URL_PLANTA",
    },
    "GEO_SONDAJES_RC": {
        "label": "Sondajes Infill RC",
        "role": "SENIOR_GEOLOGIST",
        "url_env": "DISPATCH_URL_SONDAJES",
    },
}


class DispatchRequest(BaseModel):
    alert_id: str = Field(..., description="alert_id de la alerta a despachar")
    channel: str = Field(..., description="Clave del canal de despacho")


def _role_value(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


@router.post("")
async def dispatch_alert(
    payload: DispatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    channel = CHANNELS.get(payload.channel)
    if not channel:
        raise HTTPException(
            status_code=400,
            detail=f"Canal de despacho desconocido: {payload.channel}",
        )

    result = await db.execute(
        select(Alert).where(Alert.alert_id == payload.alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alerta {payload.alert_id} no encontrada",
        )

    if not alert.acknowledged:
        raise HTTPException(
            status_code=409,
            detail="La alerta debe reconocerse antes de despachar su contramedida.",
        )

    webhook_url = os.getenv(channel.get("url_env", ""), "").strip()

    payload_out = {
        "event": "contramedida.despachada",
        "alert": {
            "id": alert.alert_id,
            "title": alert.title,
            "type": alert.alert_type,
            "severity": alert.severity,
            "bench": alert.bench,
            "block_id": alert.block_id,
            "current_value": alert.current_val,
            "threshold": alert.threshold_val,
            "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
        },
        "action_recommended": alert.action_recommended,
        "assigned_role": channel["role"],
        "dispatched_by": {
            "user_id": str(current_user.id),
            "user_name": current_user.full_name,
            "user_role": _role_value(current_user.role),
        },
        "project_id": alert.project_id,
    }

    mode = "SIMULADO"
    http_status = None
    ok = True
    if webhook_url:
        mode = "WEBHOOK"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload_out)
            http_status = resp.status_code
            ok = resp.status_code < 400
        except httpx.HTTPError:
            ok = False

    details = (
        f"Despacho {payload.channel} de alerta {alert.alert_id}: '{alert.title}' "
        f"[{channel['label']}] -> {webhook_url or 'demo local'} "
        f"({mode}, HTTP {http_status if http_status is not None else '-'})"
    )

    log = AuditLog(
        log_id=str(uuid.uuid4()),
        project_id=alert.project_id,
        timestamp=datetime.now(timezone.utc),
        user_id=str(current_user.id),
        user_name=current_user.full_name,
        user_role=_role_value(current_user.role),
        action="DISPATCH",
        module="Centro de Alertas & Dispatch",
        details=details,
        ip_address=request.client.host if request.client else "unknown",
        status="SUCCESS" if ok else "BLOCKED",
    )
    db.add(log)
    await db.commit()

    if not ok:
        raise HTTPException(
            status_code=502,
            detail=f"El webhook del canal {payload.channel} respondió HTTP {http_status}",
        )

    return {
        "success": True,
        "channel": payload.channel,
        "label": channel["label"],
        "alert_id": alert.alert_id,
        "mode": mode,
        "webhook_url": webhook_url or None,
        "http_status": http_status,
        "message": (
            "Contramedida despachada a la integración."
            if mode == "WEBHOOK"
            else "Contramedida registrada (demo: configura DISPATCH_URL_* para un webhook real)."
        ),
    }