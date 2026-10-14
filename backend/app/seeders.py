import random
import math
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models import (
    Project, Block, Drillhole, DrillholeSample,
    HyperspectralSignature, Alert, AuditLog,
    ProcessControlPoint, TrainingLossHistory, User
)
from app.auth import get_password_hash
from app.config import get_settings


async def seed_database(db: AsyncSession):
    """Seed the database with initial mock data matching the frontend mocks."""

    from sqlalchemy import select, func

    # ─── Always seed users if table is empty (for auth) ───
    settings = get_settings()
    user_count = await db.execute(select(func.count()).select_from(User))
    if user_count.scalar() == 0:
        users_data = [
            {"email": "admin@m6gemelo.cl", "password": "AdminM6*2026", "full_name": "Administrador del Sistema", "role": "ADMIN"},
            {"email": "qp.senior@m6gemelo.cl", "password": "QPSenior*2026", "full_name": "Dra. Elena Vásquez (QP)", "role": "SENIOR_GEOLOGIST"},
            {"email": "geo.junior@m6gemelo.cl", "password": "GeoJunior*2026", "full_name": "Sofía Alarcón", "role": "JUNIOR_GEOLOGIST"},
            {"email": "planificacion@m6gemelo.cl", "password": "Planifica*2026", "full_name": "Ing. Carlos Mendoza", "role": "PLANNING_ENGINEER"},
            {"email": "supervisor@m6gemelo.cl", "password": "Supervisor*2026", "full_name": "Marco Arismendi", "role": "MINE_SUPERVISOR"},
            {"email": "auditor@m6gemelo.cl", "password": "Auditor*2026", "full_name": "Dr. Alejandro Morales", "role": "VIEWER"},
        ]
        if not settings.DEMO_ACCOUNTS_ENABLED:
            users_data = []
        for u in users_data:
            db.add(User(
                email=u["email"],
                hashed_password=get_password_hash(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                is_active=True,
            ))
        await db.commit()

    if settings.INITIAL_ADMIN_EMAIL and settings.INITIAL_ADMIN_PASSWORD:
        existing_admin = await db.execute(
            select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL)
        )
        if existing_admin.scalar_one_or_none() is None:
            db.add(User(
                email=settings.INITIAL_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                full_name="Administrador del Sistema",
                role="ADMIN",
                is_active=True,
            ))
            try:
                await db.commit()
            except IntegrityError:
                # Another serverless instance may have created the same admin.
                await db.rollback()

    # Check if projects already seeded
    result = await db.execute(select(func.count()).select_from(Project))
    if result.scalar() > 0:
        return

    # 1. Projects
    projects_data = [
        {
            "project_id": "proj-m6-esperanza",
            "name": "Mina Esperanza Sur - Rajo Principal",
            "mine_site": "Distrito Minero Centinela-Caracoles",
            "country": "Chile (Región de Antofagasta)",
            "epsg_code": "EPSG:32719 (WGS 84 / UTM Zone 19S)",
            "primary_commodity": "Cu",
            "secondary_commodity": "Au",
            "cut_off_grade": 0.35,
            "high_grade_threshold": 0.80,
            "density_t_m3": 2.72,
            "total_blocks": 14500,
            "active_bench": 3170,
            "last_model_run": datetime(2026, 8, 29, 8, 30),
        },
        {
            "project_id": "proj-m6-norte",
            "name": "Rajo Centinela Norte - Fase 4B",
            "mine_site": "Complejo Minero Calama",
            "country": "Chile (Región de Antofagasta)",
            "epsg_code": "EPSG:32719 (WGS 84 / UTM Zone 19S)",
            "primary_commodity": "Cu",
            "secondary_commodity": "Mo",
            "cut_off_grade": 0.40,
            "high_grade_threshold": 0.95,
            "density_t_m3": 2.68,
            "total_blocks": 9800,
            "active_bench": 3140,
            "last_model_run": datetime(2026, 8, 28, 14, 15),
        },
        {
            "project_id": "proj-m6-penon",
            "name": "Proyecto Quebrada Blanca - Rajo Este",
            "mine_site": "Distrito Collahuasi-Pica",
            "country": "Chile (Región de Tarapacá)",
            "epsg_code": "EPSG:32719 (WGS 84 / UTM Zone 19S)",
            "primary_commodity": "Cu",
            "secondary_commodity": "Ag",
            "cut_off_grade": 0.30,
            "high_grade_threshold": 0.75,
            "density_t_m3": 2.75,
            "total_blocks": 12200,
            "active_bench": 3185,
            "last_model_run": datetime(2026, 8, 29, 2, 0),
        },
    ]

    project_objs = []
    for p in projects_data:
        proj = Project(**p)
        db.add(proj)
        project_objs.append(proj)
    await db.flush()

    # Map project_id to internal id
    proj_map = {p.project_id: p.id for p in project_objs}
    esperanza_id = proj_map["proj-m6-esperanza"]

# 2. Blocks (generate for Esperanza project)
    blocks = []
    benches = [3200, 3185, 3170, 3155, 3140, 3125, 3110, 3095, 3080, 3065]
    gridX = 12
    gridY = 12
    originX = 512400
    originY = 7416200
    blockSize = 15

    for bIdx, benchZ in enumerate(benches):
        for ix in range(gridX):
            for iy in range(gridY):
                x = originX + ix * blockSize
                y = originY + iy * blockSize
                distFromCenter = math.hypot(ix - 5.5, iy - 5.5)
                pitRadiusLimit = 5.8 + (3200 - benchZ) / 30
                if distFromCenter > pitRadiusLimit:
                    continue

                coreDist = math.hypot(ix - 5.0, iy - 6.0) + (3200 - benchZ) / 40
                baseGradeRaw = max(0.08, 1.45 * math.exp(-coreDist * 0.38) + (math.sin(ix * 0.7) * math.cos(iy * 0.8) * 0.18))
                cu_base = round(baseGradeRaw, 3)

                nearest_drillhole_m = max(8, round(coreDist * 9.5 + abs(ix - iy) * 4.2, 1))
                epistemic_unc = round(0.04 + (nearest_drillhole_m / 100) * 0.22 + (bIdx * 0.02), 3)
                aleatoric_unc = round(0.03 + 0.04 * random.random(), 3)
                total_unc = round(math.hypot(epistemic_unc, aleatoric_unc), 3)

                correctionFactor = (math.cos((ix + iy + bIdx) * 1.1) * 0.12) + (0.08 if nearest_drillhole_m < 25 else -0.05)
                cu_bayesian = round(max(0.05, cu_base + correctionFactor), 3)
                deviation_pct = round(((cu_bayesian - cu_base) / cu_base) * 100, 1) if cu_base > 0 else 0

                p10 = round(max(0.02, cu_bayesian - 1.28 * total_unc), 3)
                p50 = cu_bayesian
                p90 = round(cu_bayesian + 1.28 * total_unc, 3)
                cv = total_unc / cu_bayesian if cu_bayesian > 0 else 0
                confidence_pct = round(min(99.5, max(45, (1 - min(1, cv * 0.7)) * 100)), 1)

                # Determine lithology, alteration, mineral
                if coreDist < 2.5:
                    lithology = "Brecha Hidrotermal"
                    alteration = "Potásica"
                    dominant_mineral = "Bornita"
                    hyperMineral = "Biotita Hidrotermal + Bornita (SWIR 2200nm)"
                elif coreDist < 4.5:
                    lithology = "Pórfido Cuprífero"
                    alteration = "Fílica"
                    dominant_mineral = "Calcopirita"
                    hyperMineral = "Sericita / Illita Fílica (2206nm)"
                elif benchZ >= 3185 and iy > 7:
                    lithology = "Skarn Mineralizado"
                    alteration = "Supérgena"
                    dominant_mineral = "Crisocola"
                    hyperMineral = "Crisocola + Malaquita (VNIR 680-850nm)"
                elif coreDist > 6.0:
                    lithology = "Andesita Huinquintipa"
                    alteration = "Propilítica"
                    dominant_mineral = "Pirita"
                    hyperMineral = "Clorita + Epidota (2250nm/2330nm)"
                else:
                    lithology = "Pórfido Cuprífero"
                    alteration = "Fílica"
                    dominant_mineral = "Calcopirita"
                    hyperMineral = "Sericita / Illita Fílica (2206nm)"

                if nearest_drillhole_m <= 25 and epistemic_unc < 0.08:
                    category = "Measured"
                elif nearest_drillhole_m <= 50 and epistemic_unc < 0.16:
                    category = "Indicated"
                elif nearest_drillhole_m <= 90:
                    category = "Inferred"
                else:
                    category = "Unclassified"

                tonnage = round(blockSize * blockSize * blockSize * 2.72)
                au_base = round(cu_base * 0.28 + random.random() * 0.05, 3)
                au_bayesian = round(cu_bayesian * 0.29 + random.random() * 0.04, 3)

                block = Block(
                    block_id=f"BLK-{benchZ}-{ix}-{iy}",
                    project_id=esperanza_id,
                    x=x, y=y, z=benchZ, bench=benchZ,
                    dx=blockSize, dy=blockSize, dz=blockSize,
                    cu_base=cu_base, cu_bayesian=cu_bayesian,
                    cu_variance=round(total_unc * total_unc, 4),
                    au_base=au_base, au_bayesian=au_bayesian,
                    epistemic_unc=epistemic_unc, aleatoric_unc=aleatoric_unc,
                    total_unc=total_unc, p10=p10, p50=p50, p90=p90,
                    confidence_pct=confidence_pct, tonnage=tonnage,
                    density=2.72, lithology=lithology, alteration=alteration,
                    hyperspectral_mineral=hyperMineral,
                    dominant_mineral=dominant_mineral,
                    category=category, deviation_pct=deviation_pct,
                    nearest_drillhole_m=nearest_drillhole_m,
                )
                blocks.append(block)

    for b in blocks:
        db.add(b)
    await db.flush()

    # 3. Drillholes
    drillholes_data = [
        {
            "hole_id": "DDH-2026-081", "hole_type": "DIAMOND_DDH",
            "x": 512460, "y": 7416260, "z": 3205, "total_depth_m": 140,
            "azimuth": 180, "dip": -75, "date_drilled": date(2026, 8, 12),
            "samples": [
                {"from_m": 0, "to_m": 15, "length_m": 15, "cu_pct": 0.42, "au_gpt": 0.12, "lithology": "Andesita Huinquintipa", "alteration": "Propilítica", "recovery_pct": 98.5, "rqd_pct": 82},
                {"from_m": 15, "to_m": 45, "length_m": 30, "cu_pct": 0.98, "au_gpt": 0.31, "lithology": "Pórfido Cuprífero", "alteration": "Fílica", "recovery_pct": 99.1, "rqd_pct": 88},
                {"from_m": 45, "to_m": 90, "length_m": 45, "cu_pct": 1.45, "au_gpt": 0.48, "lithology": "Brecha Hidrotermal", "alteration": "Potásica", "recovery_pct": 99.4, "rqd_pct": 92},
                {"from_m": 90, "to_m": 140, "length_m": 50, "cu_pct": 1.15, "au_gpt": 0.36, "lithology": "Pórfido Cuprífero", "alteration": "Potásica", "recovery_pct": 98.0, "rqd_pct": 85},
            ],
        },
        {
            "hole_id": "DDH-2026-082", "hole_type": "DIAMOND_DDH",
            "x": 512500, "y": 7416300, "z": 3202, "total_depth_m": 120,
            "azimuth": 210, "dip": -80, "date_drilled": date(2026, 8, 15),
            "samples": [
                {"from_m": 0, "to_m": 20, "length_m": 20, "cu_pct": 0.35, "au_gpt": 0.09, "lithology": "Andesita Huinquintipa", "alteration": "Propilítica", "recovery_pct": 97.2, "rqd_pct": 78},
                {"from_m": 20, "to_m": 60, "length_m": 40, "cu_pct": 0.72, "au_gpt": 0.22, "lithology": "Pórfido Cuprífero", "alteration": "Fílica", "recovery_pct": 98.7, "rqd_pct": 84},
                {"from_m": 60, "to_m": 120, "length_m": 60, "cu_pct": 1.28, "au_gpt": 0.39, "lithology": "Brecha Hidrotermal", "alteration": "Potásica", "recovery_pct": 99.0, "rqd_pct": 90},
            ],
        },
        {
            "hole_id": "RC-2026-114", "hole_type": "REVERSE_CIRCULATION_RC",
            "x": 512420, "y": 7416210, "z": 3185, "total_depth_m": 80,
            "azimuth": 0, "dip": -90, "date_drilled": date(2026, 8, 20),
            "samples": [
                {"from_m": 0, "to_m": 25, "length_m": 25, "cu_pct": 1.12, "au_gpt": 0.34, "lithology": "Brecha Hidrotermal", "alteration": "Potásica", "recovery_pct": 95.0, "rqd_pct": 75},
                {"from_m": 25, "to_m": 80, "length_m": 55, "cu_pct": 1.34, "au_gpt": 0.42, "lithology": "Brecha Hidrotermal", "alteration": "Potásica", "recovery_pct": 96.2, "rqd_pct": 80},
            ],
        },
        {
            "hole_id": "BLAST-3170-A12", "hole_type": "BLASTHOLE_TRICONO",
            "x": 512475, "y": 7416245, "z": 3170, "total_depth_m": 16.5,
            "azimuth": 0, "dip": -90, "date_drilled": date(2026, 8, 28),
            "samples": [
                {"from_m": 0, "to_m": 16.5, "length_m": 16.5, "cu_pct": 1.22, "au_gpt": 0.38, "lithology": "Brecha Hidrotermal", "alteration": "Potásica", "recovery_pct": 99.5, "rqd_pct": 91},
            ],
        },
    ]

    for dh_data in drillholes_data:
        samples = dh_data.pop("samples")
        dh = Drillhole(project_id=esperanza_id, **dh_data)
        db.add(dh)
        await db.flush()
        for s in samples:
            db.add(DrillholeSample(drillhole_id=dh.id, **s))

    # 4. Hyperspectral Signatures
    hyperspectral_data = [
        {
            "mineral": "Illita / Sericita (Alteración Fílica)", "code": "ILL-F", "color": "#38bdf8",
            "spectrum": [
                {"wavelength": 450, "reflectance": 0.18}, {"wavelength": 650, "reflectance": 0.28},
                {"wavelength": 850, "reflectance": 0.38}, {"wavelength": 1050, "reflectance": 0.44},
                {"wavelength": 1400, "reflectance": 0.22}, {"wavelength": 1600, "reflectance": 0.52},
                {"wavelength": 1900, "reflectance": 0.19}, {"wavelength": 2160, "reflectance": 0.48},
                {"wavelength": 2206, "reflectance": 0.12}, {"wavelength": 2250, "reflectance": 0.46},
                {"wavelength": 2350, "reflectance": 0.35}, {"wavelength": 2500, "reflectance": 0.24},
            ],
        },
        {
            "mineral": "Biotita Hidrotermal / Potásica", "code": "BIO-POT", "color": "#f59e0b",
            "spectrum": [
                {"wavelength": 450, "reflectance": 0.10}, {"wavelength": 650, "reflectance": 0.18},
                {"wavelength": 850, "reflectance": 0.25}, {"wavelength": 1050, "reflectance": 0.31},
                {"wavelength": 1400, "reflectance": 0.20}, {"wavelength": 1600, "reflectance": 0.36},
                {"wavelength": 1900, "reflectance": 0.28}, {"wavelength": 2160, "reflectance": 0.38},
                {"wavelength": 2250, "reflectance": 0.22}, {"wavelength": 2325, "reflectance": 0.14},
                {"wavelength": 2385, "reflectance": 0.18}, {"wavelength": 2500, "reflectance": 0.15},
            ],
        },
        {
            "mineral": "Clorita + Epidota (Propilítica)", "code": "CHL-EP", "color": "#10b981",
            "spectrum": [
                {"wavelength": 450, "reflectance": 0.12}, {"wavelength": 650, "reflectance": 0.22},
                {"wavelength": 850, "reflectance": 0.19}, {"wavelength": 1050, "reflectance": 0.33},
                {"wavelength": 1400, "reflectance": 0.25}, {"wavelength": 1600, "reflectance": 0.44},
                {"wavelength": 1900, "reflectance": 0.30}, {"wavelength": 2250, "reflectance": 0.15},
                {"wavelength": 2335, "reflectance": 0.11}, {"wavelength": 2450, "reflectance": 0.26},
                {"wavelength": 2500, "reflectance": 0.20},
            ],
        },
        {
            "mineral": "Crisocola + Malaquita (Óxidos Supérgenos)", "code": "OX-CU", "color": "#06b6d4",
            "spectrum": [
                {"wavelength": 450, "reflectance": 0.22}, {"wavelength": 650, "reflectance": 0.45},
                {"wavelength": 850, "reflectance": 0.14}, {"wavelength": 1050, "reflectance": 0.28},
                {"wavelength": 1400, "reflectance": 0.15}, {"wavelength": 1600, "reflectance": 0.38},
                {"wavelength": 1900, "reflectance": 0.12}, {"wavelength": 2160, "reflectance": 0.34},
                {"wavelength": 2270, "reflectance": 0.18}, {"wavelength": 2380, "reflectance": 0.32},
                {"wavelength": 2500, "reflectance": 0.25},
            ],
        },
    ]

    for h in hyperspectral_data:
        db.add(HyperspectralSignature(project_id=esperanza_id, **h))

    # 5. Alerts
    alerts_data = [
        {
            "alert_id": "ALT-1049", "alert_type": "HIGH_UNCERTAINTY", "severity": "CRITICAL",
            "bench": 3155, "block_id": "BLK-3155-10-09",
            "title": "Zona de Alta Incertidumbre Epistémica (CV > 32%)",
            "description": "Bloque con espaciamiento de sondajes > 75m en el flanco Este. Requiere 2 pozos infill de control antes de voladura programada para el 04-Sep.",
            "current_val": "34.2% CV (σ = 0.28% Cu)", "threshold_val": "Max 20.0% CV",
            "timestamp": datetime(2026, 8, 29, 7, 15), "acknowledged": False,
            "assigned_role": "SENIOR_GEOLOGIST",
            "action_recommended": "Programar sondaje RC infill de 25m en coordenadas 512520E, 7416340N.",
        },
        {
            "alert_id": "ALT-1048", "alert_type": "GRADE_DEVIATION", "severity": "WARNING",
            "bench": 3170, "block_id": "BLK-3170-04-05",
            "title": "Desviación Positiva de Ley (> +24% vs Kriging Base)",
            "description": "El modelo multimodal bayesiano detecta enriquecimiento supérgeno no capturado por el modelo de largo plazo debido a respuesta espectral de crisocola.",
            "current_val": "1.24% Cu (Base: 0.98% Cu)", "threshold_val": "Delta > ±15%",
            "timestamp": datetime(2026, 8, 29, 5, 40), "acknowledged": True,
            "assigned_role": "PLANNING_ENGINEER",
            "action_recommended": "Reclasificar bloque de Stock Baja Ley a Alimentación Directa Planta Concentradora.",
        },
        {
            "alert_id": "ALT-1047", "alert_type": "DILUTION_RISK", "severity": "WARNING",
            "bench": 3185, "block_id": "BLK-3185-02-08",
            "title": "Riesgo de Dilución en Contacto Litológico",
            "description": "Contacto abrupto entre Skarn mineralizado y Andesita Huinquintipa estéril. Intervalo P10-P90 amplio [0.22% - 0.78% Cu].",
            "current_val": "P10 = 0.22% Cu (Sub-económico)", "threshold_val": "Cut-off = 0.35% Cu",
            "timestamp": datetime(2026, 8, 28, 19, 20), "acknowledged": False,
            "assigned_role": "MINE_SUPERVISOR",
            "action_recommended": "Ajustar línea de marcación de pala (dig line) con buffer de seguridad de 3.5m.",
        },
    ]

    for a in alerts_data:
        db.add(Alert(project_id=esperanza_id, **a))

    # 6. Audit Logs
    audit_logs_data = [
        {
            "log_id": "LOG-9921", "timestamp": datetime(2026, 8, 29, 8, 30, 14),
            "user_id": "usr-geo-01", "user_name": "Dra. Elena Vasquez",
            "user_role": "SENIOR_GEOLOGIST", "action": "RUN_BAYESIAN_INFERENCE",
            "module": "Motor Bayesiano MFM v3.2",
            "details": "Ejecutó inferencia variacional MFM en Banco 3170 (124 bloques, 200 muestras MC). Tiempo: 1.42s.",
            "ip_address": "10.24.112.45", "status": "SUCCESS",
        },
        {
            "log_id": "LOG-9920", "timestamp": datetime(2026, 8, 29, 7, 45, 2),
            "user_id": "usr-plan-04", "user_name": "Ing. Carlos Mendoza",
            "user_role": "PLANNING_ENGINEER", "action": "EXPORT_REPORT_JORC",
            "module": "Generador de Reportes",
            "details": "Exportó Reporte Técnico PDF Compliance JORC 2012 para Fase 4B.",
            "ip_address": "10.24.112.89", "status": "SUCCESS",
        },
        {
            "log_id": "LOG-9919", "timestamp": datetime(2026, 8, 29, 6, 12, 33),
            "user_id": "usr-sup-02", "user_name": "Marco Arismendi",
            "user_role": "MINE_SUPERVISOR", "action": "ACKNOWLEDGE_ALERT",
            "module": "Alertas y Despacho",
            "details": "Confirmó lectura de Alerta ALT-1048 (Desviación Positiva de Ley en Banco 3170).",
            "ip_address": "10.24.118.12", "status": "SUCCESS",
        },
        {
            "log_id": "LOG-9918", "timestamp": datetime(2026, 8, 28, 22, 10, 19),
            "user_id": "usr-geo-03", "user_name": "Sofia Alarcon",
            "user_role": "JUNIOR_GEOLOGIST", "action": "UPLOAD_DRILLHOLE_ASSAY",
            "module": "Gestión Geoespacial",
            "details": "Cargó 48 intervalos de leyes para sondeo RC-2026-114.",
            "ip_address": "10.24.112.50", "status": "SUCCESS",
        },
    ]

    for log in audit_logs_data:
        db.add(AuditLog(project_id=esperanza_id, **log))

    # 7. Process Control Points — SPC data for ALL benches (geologically realistic)
    # Ley patterns: 3200/3185 = lower (peripheral), 3170/3155 = high (core), 3140/3125 = moderate
    pcp_data = [
        {"point_id": "BL-3200-01", "blast_id": "TR-3200-01", "timestamp": datetime(2026, 7, 2), "bench": 3200, "tonnage": 38936, "plant_feed_grade": 0.58, "predicted_base_krig": 0.5, "predicted_bayesian": 0.56, "residual_base": 0.08, "residual_bayesian": 0.02, "cusum_high": 0.07, "cusum_low": 0.0, "ewma_grade": 0.6, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-02", "blast_id": "TR-3200-02", "timestamp": datetime(2026, 7, 4), "bench": 3200, "tonnage": 38338, "plant_feed_grade": 0.28, "predicted_base_krig": 0.18, "predicted_bayesian": 0.26, "residual_base": 0.09, "residual_bayesian": 0.02, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.47, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-03", "blast_id": "TR-3200-03", "timestamp": datetime(2026, 7, 6), "bench": 3200, "tonnage": 40591, "plant_feed_grade": 0.46, "predicted_base_krig": 0.37, "predicted_bayesian": 0.44, "residual_base": 0.09, "residual_bayesian": 0.03, "cusum_high": 0.14, "cusum_low": 0.0, "ewma_grade": 0.42, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-04", "blast_id": "TR-3200-04", "timestamp": datetime(2026, 7, 9), "bench": 3200, "tonnage": 40294, "plant_feed_grade": 0.46, "predicted_base_krig": 0.37, "predicted_bayesian": 0.43, "residual_base": 0.08, "residual_bayesian": 0.03, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.48, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-05", "blast_id": "TR-3200-05", "timestamp": datetime(2026, 7, 14), "bench": 3200, "tonnage": 42105, "plant_feed_grade": 0.38, "predicted_base_krig": 0.31, "predicted_bayesian": 0.34, "residual_base": 0.07, "residual_bayesian": 0.04, "cusum_high": 0.15, "cusum_low": 0.0, "ewma_grade": 0.51, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-06", "blast_id": "TR-3200-06", "timestamp": datetime(2026, 7, 16), "bench": 3200, "tonnage": 39093, "plant_feed_grade": 0.66, "predicted_base_krig": 0.59, "predicted_bayesian": 0.62, "residual_base": 0.07, "residual_bayesian": 0.04, "cusum_high": 0.21, "cusum_low": 0.0, "ewma_grade": 0.46, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-07", "blast_id": "TR-3200-07", "timestamp": datetime(2026, 7, 20), "bench": 3200, "tonnage": 43559, "plant_feed_grade": 0.56, "predicted_base_krig": 0.44, "predicted_bayesian": 0.49, "residual_base": 0.12, "residual_bayesian": 0.07, "cusum_high": 0.31, "cusum_low": 0.0, "ewma_grade": 0.47, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-08", "blast_id": "TR-3200-08", "timestamp": datetime(2026, 7, 22), "bench": 3200, "tonnage": 42972, "plant_feed_grade": 0.51, "predicted_base_krig": 0.42, "predicted_bayesian": 0.45, "residual_base": 0.09, "residual_bayesian": 0.06, "cusum_high": 0.29, "cusum_low": 0.0, "ewma_grade": 0.48, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-09", "blast_id": "TR-3200-09", "timestamp": datetime(2026, 7, 24), "bench": 3200, "tonnage": 38093, "plant_feed_grade": 0.34, "predicted_base_krig": 0.28, "predicted_bayesian": 0.29, "residual_base": 0.06, "residual_bayesian": 0.05, "cusum_high": 0.15, "cusum_low": 0.0, "ewma_grade": 0.49, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-10", "blast_id": "TR-3200-10", "timestamp": datetime(2026, 7, 29), "bench": 3200, "tonnage": 38444, "plant_feed_grade": 0.59, "predicted_base_krig": 0.54, "predicted_bayesian": 0.58, "residual_base": 0.05, "residual_bayesian": 0.01, "cusum_high": 0.24, "cusum_low": 0.0, "ewma_grade": 0.56, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-11", "blast_id": "TR-3200-11", "timestamp": datetime(2026, 7, 31), "bench": 3200, "tonnage": 41995, "plant_feed_grade": 0.41, "predicted_base_krig": 0.33, "predicted_bayesian": 0.41, "residual_base": 0.08, "residual_bayesian": 0.0, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 0.46, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-12", "blast_id": "TR-3200-12", "timestamp": datetime(2026, 8, 4), "bench": 3200, "tonnage": 41367, "plant_feed_grade": 0.4, "predicted_base_krig": 0.31, "predicted_bayesian": 0.38, "residual_base": 0.08, "residual_bayesian": 0.01, "cusum_high": 0.02, "cusum_low": 0.0, "ewma_grade": 0.56, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-13", "blast_id": "TR-3200-13", "timestamp": datetime(2026, 8, 5), "bench": 3200, "tonnage": 40852, "plant_feed_grade": 0.5, "predicted_base_krig": 0.39, "predicted_bayesian": 0.47, "residual_base": 0.11, "residual_bayesian": 0.03, "cusum_high": 0.15, "cusum_low": 0.0, "ewma_grade": 0.51, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-14", "blast_id": "TR-3200-14", "timestamp": datetime(2026, 8, 10), "bench": 3200, "tonnage": 39372, "plant_feed_grade": 0.49, "predicted_base_krig": 0.42, "predicted_bayesian": 0.49, "residual_base": 0.07, "residual_bayesian": 0.0, "cusum_high": 0.08, "cusum_low": 0.0, "ewma_grade": 0.49, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-15", "blast_id": "TR-3200-15", "timestamp": datetime(2026, 8, 12), "bench": 3200, "tonnage": 39119, "plant_feed_grade": 0.58, "predicted_base_krig": 0.53, "predicted_bayesian": 0.56, "residual_base": 0.05, "residual_bayesian": 0.02, "cusum_high": 0.31, "cusum_low": 0.0, "ewma_grade": 0.54, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-16", "blast_id": "TR-3200-16", "timestamp": datetime(2026, 8, 16), "bench": 3200, "tonnage": 39632, "plant_feed_grade": 0.43, "predicted_base_krig": 0.34, "predicted_bayesian": 0.41, "residual_base": 0.09, "residual_bayesian": 0.02, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 0.51, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-17", "blast_id": "TR-3200-17", "timestamp": datetime(2026, 8, 17), "bench": 3200, "tonnage": 40504, "plant_feed_grade": 0.56, "predicted_base_krig": 0.48, "predicted_bayesian": 0.53, "residual_base": 0.07, "residual_bayesian": 0.03, "cusum_high": 0.24, "cusum_low": 0.0, "ewma_grade": 0.51, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-18", "blast_id": "TR-3200-18", "timestamp": datetime(2026, 8, 20), "bench": 3200, "tonnage": 41348, "plant_feed_grade": 0.41, "predicted_base_krig": 0.31, "predicted_bayesian": 0.37, "residual_base": 0.1, "residual_bayesian": 0.04, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.49, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-19", "blast_id": "TR-3200-19", "timestamp": datetime(2026, 8, 23), "bench": 3200, "tonnage": 38888, "plant_feed_grade": 0.42, "predicted_base_krig": 0.31, "predicted_bayesian": 0.41, "residual_base": 0.1, "residual_bayesian": 0.01, "cusum_high": 0.04, "cusum_low": 0.0, "ewma_grade": 0.57, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-20", "blast_id": "TR-3200-20", "timestamp": datetime(2026, 8, 27), "bench": 3200, "tonnage": 41806, "plant_feed_grade": 0.51, "predicted_base_krig": 0.44, "predicted_bayesian": 0.48, "residual_base": 0.07, "residual_bayesian": 0.03, "cusum_high": 0.05, "cusum_low": 0.0, "ewma_grade": 0.51, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-21", "blast_id": "TR-3200-21", "timestamp": datetime(2026, 8, 31), "bench": 3200, "tonnage": 42569, "plant_feed_grade": 0.56, "predicted_base_krig": 0.48, "predicted_bayesian": 0.55, "residual_base": 0.08, "residual_bayesian": 0.01, "cusum_high": 0.1, "cusum_low": 0.0, "ewma_grade": 0.46, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-22", "blast_id": "TR-3200-22", "timestamp": datetime(2026, 9, 1), "bench": 3200, "tonnage": 42898, "plant_feed_grade": 0.5, "predicted_base_krig": 0.47, "predicted_bayesian": 0.47, "residual_base": 0.04, "residual_bayesian": 0.03, "cusum_high": 0.05, "cusum_low": 0.0, "ewma_grade": 0.53, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-23", "blast_id": "TR-3200-23", "timestamp": datetime(2026, 9, 5), "bench": 3200, "tonnage": 39321, "plant_feed_grade": 0.75, "predicted_base_krig": 0.67, "predicted_bayesian": 0.71, "residual_base": 0.08, "residual_bayesian": 0.04, "cusum_high": 0.28, "cusum_low": 0.0, "ewma_grade": 0.56, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-24", "blast_id": "TR-3200-24", "timestamp": datetime(2026, 9, 8), "bench": 3200, "tonnage": 40320, "plant_feed_grade": 0.6, "predicted_base_krig": 0.48, "predicted_bayesian": 0.58, "residual_base": 0.12, "residual_bayesian": 0.02, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 0.47, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-25", "blast_id": "TR-3200-25", "timestamp": datetime(2026, 9, 12), "bench": 3200, "tonnage": 42174, "plant_feed_grade": 0.66, "predicted_base_krig": 0.61, "predicted_bayesian": 0.63, "residual_base": 0.05, "residual_bayesian": 0.03, "cusum_high": 0.28, "cusum_low": 0.0, "ewma_grade": 0.45, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-26", "blast_id": "TR-3200-26", "timestamp": datetime(2026, 9, 13), "bench": 3200, "tonnage": 38558, "plant_feed_grade": 0.55, "predicted_base_krig": 0.51, "predicted_bayesian": 0.49, "residual_base": 0.04, "residual_bayesian": 0.06, "cusum_high": 0.29, "cusum_low": 0.0, "ewma_grade": 0.53, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-27", "blast_id": "TR-3200-27", "timestamp": datetime(2026, 9, 17), "bench": 3200, "tonnage": 43382, "plant_feed_grade": 0.35, "predicted_base_krig": 0.3, "predicted_bayesian": 0.34, "residual_base": 0.04, "residual_bayesian": 0.0, "cusum_high": 0.16, "cusum_low": 0.0, "ewma_grade": 0.48, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-28", "blast_id": "TR-3200-28", "timestamp": datetime(2026, 9, 20), "bench": 3200, "tonnage": 38030, "plant_feed_grade": 0.44, "predicted_base_krig": 0.37, "predicted_bayesian": 0.41, "residual_base": 0.07, "residual_bayesian": 0.02, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 0.48, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-29", "blast_id": "TR-3200-29", "timestamp": datetime(2026, 9, 22), "bench": 3200, "tonnage": 39423, "plant_feed_grade": 0.65, "predicted_base_krig": 0.61, "predicted_bayesian": 0.63, "residual_base": 0.04, "residual_bayesian": 0.02, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 0.47, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-30", "blast_id": "TR-3200-30", "timestamp": datetime(2026, 9, 27), "bench": 3200, "tonnage": 41255, "plant_feed_grade": 0.68, "predicted_base_krig": 0.58, "predicted_bayesian": 0.63, "residual_base": 0.1, "residual_bayesian": 0.05, "cusum_high": 0.2, "cusum_low": 0.0, "ewma_grade": 0.58, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-31", "blast_id": "TR-3200-31", "timestamp": datetime(2026, 9, 30), "bench": 3200, "tonnage": 43352, "plant_feed_grade": 0.41, "predicted_base_krig": 0.31, "predicted_bayesian": 0.38, "residual_base": 0.1, "residual_bayesian": 0.03, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 0.54, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-32", "blast_id": "TR-3200-32", "timestamp": datetime(2026, 10, 3), "bench": 3200, "tonnage": 39381, "plant_feed_grade": 0.68, "predicted_base_krig": 0.56, "predicted_bayesian": 0.66, "residual_base": 0.12, "residual_bayesian": 0.01, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 0.54, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-33", "blast_id": "TR-3200-33", "timestamp": datetime(2026, 10, 4), "bench": 3200, "tonnage": 42486, "plant_feed_grade": 0.52, "predicted_base_krig": 0.44, "predicted_bayesian": 0.5, "residual_base": 0.07, "residual_bayesian": 0.02, "cusum_high": 0.29, "cusum_low": 0.0, "ewma_grade": 0.5, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-34", "blast_id": "TR-3200-34", "timestamp": datetime(2026, 10, 9), "bench": 3200, "tonnage": 43106, "plant_feed_grade": 0.58, "predicted_base_krig": 0.49, "predicted_bayesian": 0.53, "residual_base": 0.08, "residual_bayesian": 0.05, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 0.44, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-35", "blast_id": "TR-3200-35", "timestamp": datetime(2026, 10, 12), "bench": 3200, "tonnage": 38583, "plant_feed_grade": 0.61, "predicted_base_krig": 0.53, "predicted_bayesian": 0.59, "residual_base": 0.08, "residual_bayesian": 0.02, "cusum_high": 0.35, "cusum_low": 0.0, "ewma_grade": 0.61, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-36", "blast_id": "TR-3200-36", "timestamp": datetime(2026, 10, 15), "bench": 3200, "tonnage": 42182, "plant_feed_grade": 0.53, "predicted_base_krig": 0.41, "predicted_bayesian": 0.5, "residual_base": 0.11, "residual_bayesian": 0.02, "cusum_high": 0.23, "cusum_low": 0.0, "ewma_grade": 0.55, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-37", "blast_id": "TR-3200-37", "timestamp": datetime(2026, 10, 17), "bench": 3200, "tonnage": 41669, "plant_feed_grade": 0.3, "predicted_base_krig": 0.24, "predicted_bayesian": 0.24, "residual_base": 0.07, "residual_bayesian": 0.06, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.49, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-38", "blast_id": "TR-3200-38", "timestamp": datetime(2026, 10, 21), "bench": 3200, "tonnage": 38304, "plant_feed_grade": 0.38, "predicted_base_krig": 0.31, "predicted_bayesian": 0.34, "residual_base": 0.07, "residual_bayesian": 0.03, "cusum_high": 0.04, "cusum_low": 0.0, "ewma_grade": 0.49, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-39", "blast_id": "TR-3200-39", "timestamp": datetime(2026, 10, 24), "bench": 3200, "tonnage": 40793, "plant_feed_grade": 0.43, "predicted_base_krig": 0.34, "predicted_bayesian": 0.39, "residual_base": 0.09, "residual_bayesian": 0.04, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 0.52, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-40", "blast_id": "TR-3200-40", "timestamp": datetime(2026, 10, 25), "bench": 3200, "tonnage": 39959, "plant_feed_grade": 0.54, "predicted_base_krig": 0.46, "predicted_bayesian": 0.52, "residual_base": 0.08, "residual_bayesian": 0.02, "cusum_high": 0.1, "cusum_low": 0.0, "ewma_grade": 0.43, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-41", "blast_id": "TR-3200-41", "timestamp": datetime(2026, 10, 30), "bench": 3200, "tonnage": 40468, "plant_feed_grade": 0.51, "predicted_base_krig": 0.45, "predicted_bayesian": 0.48, "residual_base": 0.06, "residual_bayesian": 0.04, "cusum_high": 0.2, "cusum_low": 0.0, "ewma_grade": 0.54, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-42", "blast_id": "TR-3200-42", "timestamp": datetime(2026, 11, 2), "bench": 3200, "tonnage": 40633, "plant_feed_grade": 0.28, "predicted_base_krig": 0.2, "predicted_bayesian": 0.23, "residual_base": 0.07, "residual_bayesian": 0.04, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.56, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-43", "blast_id": "TR-3200-43", "timestamp": datetime(2026, 11, 3), "bench": 3200, "tonnage": 38563, "plant_feed_grade": 0.73, "predicted_base_krig": 0.63, "predicted_bayesian": 0.67, "residual_base": 0.1, "residual_bayesian": 0.06, "cusum_high": 0.31, "cusum_low": 0.0, "ewma_grade": 0.5, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-44", "blast_id": "TR-3200-44", "timestamp": datetime(2026, 11, 8), "bench": 3200, "tonnage": 39486, "plant_feed_grade": 0.57, "predicted_base_krig": 0.53, "predicted_bayesian": 0.51, "residual_base": 0.03, "residual_bayesian": 0.06, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 0.61, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-45", "blast_id": "TR-3200-45", "timestamp": datetime(2026, 11, 11), "bench": 3200, "tonnage": 40949, "plant_feed_grade": 0.57, "predicted_base_krig": 0.52, "predicted_bayesian": 0.52, "residual_base": 0.06, "residual_bayesian": 0.05, "cusum_high": 0.14, "cusum_low": 0.0, "ewma_grade": 0.52, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-46", "blast_id": "TR-3200-46", "timestamp": datetime(2026, 11, 14), "bench": 3200, "tonnage": 38091, "plant_feed_grade": 0.77, "predicted_base_krig": 0.68, "predicted_bayesian": 0.74, "residual_base": 0.09, "residual_bayesian": 0.04, "cusum_high": 0.29, "cusum_low": 0.0, "ewma_grade": 0.55, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-47", "blast_id": "TR-3200-47", "timestamp": datetime(2026, 11, 17), "bench": 3200, "tonnage": 41514, "plant_feed_grade": 0.57, "predicted_base_krig": 0.52, "predicted_bayesian": 0.53, "residual_base": 0.05, "residual_bayesian": 0.03, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 0.52, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-48", "blast_id": "TR-3200-48", "timestamp": datetime(2026, 11, 20), "bench": 3200, "tonnage": 42923, "plant_feed_grade": 0.61, "predicted_base_krig": 0.58, "predicted_bayesian": 0.58, "residual_base": 0.03, "residual_bayesian": 0.03, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 0.51, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-49", "blast_id": "TR-3200-49", "timestamp": datetime(2026, 11, 21), "bench": 3200, "tonnage": 40263, "plant_feed_grade": 0.38, "predicted_base_krig": 0.32, "predicted_bayesian": 0.33, "residual_base": 0.06, "residual_bayesian": 0.05, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.49, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3200-50", "blast_id": "TR-3200-50", "timestamp": datetime(2026, 11, 25), "bench": 3200, "tonnage": 38139, "plant_feed_grade": 0.46, "predicted_base_krig": 0.39, "predicted_bayesian": 0.45, "residual_base": 0.07, "residual_bayesian": 0.01, "cusum_high": 0.06, "cusum_low": 0.0, "ewma_grade": 0.5, "ucl": 0.75, "lcl": 0.25, "target_grade": 0.5},
        {"point_id": "BL-3185-01", "blast_id": "TR-3185-01", "timestamp": datetime(2026, 7, 1), "bench": 3185, "tonnage": 44235, "plant_feed_grade": 1.14, "predicted_base_krig": 1.02, "predicted_bayesian": 1.11, "residual_base": 0.12, "residual_bayesian": 0.03, "cusum_high": 0.45, "cusum_low": 0.0, "ewma_grade": 0.84, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-02", "blast_id": "TR-3185-02", "timestamp": datetime(2026, 7, 5), "bench": 3185, "tonnage": 49943, "plant_feed_grade": 0.73, "predicted_base_krig": 0.59, "predicted_bayesian": 0.7, "residual_base": 0.14, "residual_bayesian": 0.03, "cusum_high": 0.08, "cusum_low": 0.0, "ewma_grade": 0.88, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-03", "blast_id": "TR-3185-03", "timestamp": datetime(2026, 7, 9), "bench": 3185, "tonnage": 48079, "plant_feed_grade": 1.01, "predicted_base_krig": 0.89, "predicted_bayesian": 0.94, "residual_base": 0.11, "residual_bayesian": 0.07, "cusum_high": 0.37, "cusum_low": 0.0, "ewma_grade": 0.87, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-04", "blast_id": "TR-3185-04", "timestamp": datetime(2026, 7, 10), "bench": 3185, "tonnage": 46335, "plant_feed_grade": 1.05, "predicted_base_krig": 0.93, "predicted_bayesian": 1.02, "residual_base": 0.12, "residual_bayesian": 0.03, "cusum_high": 0.43, "cusum_low": 0.0, "ewma_grade": 0.83, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-05", "blast_id": "TR-3185-05", "timestamp": datetime(2026, 7, 15), "bench": 3185, "tonnage": 46690, "plant_feed_grade": 0.81, "predicted_base_krig": 0.67, "predicted_bayesian": 0.81, "residual_base": 0.14, "residual_bayesian": 0.0, "cusum_high": 0.23, "cusum_low": 0.0, "ewma_grade": 0.9, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-06", "blast_id": "TR-3185-06", "timestamp": datetime(2026, 7, 16), "bench": 3185, "tonnage": 49811, "plant_feed_grade": 0.63, "predicted_base_krig": 0.52, "predicted_bayesian": 0.63, "residual_base": 0.11, "residual_bayesian": 0.0, "cusum_high": 0.19, "cusum_low": 0.0, "ewma_grade": 0.87, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-07", "blast_id": "TR-3185-07", "timestamp": datetime(2026, 7, 20), "bench": 3185, "tonnage": 44436, "plant_feed_grade": 0.73, "predicted_base_krig": 0.61, "predicted_bayesian": 0.69, "residual_base": 0.11, "residual_bayesian": 0.04, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 0.82, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-08", "blast_id": "TR-3185-08", "timestamp": datetime(2026, 7, 23), "bench": 3185, "tonnage": 49178, "plant_feed_grade": 0.86, "predicted_base_krig": 0.7, "predicted_bayesian": 0.83, "residual_base": 0.16, "residual_bayesian": 0.03, "cusum_high": 0.31, "cusum_low": 0.0, "ewma_grade": 0.78, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-09", "blast_id": "TR-3185-09", "timestamp": datetime(2026, 7, 27), "bench": 3185, "tonnage": 49438, "plant_feed_grade": 0.75, "predicted_base_krig": 0.67, "predicted_bayesian": 0.67, "residual_base": 0.08, "residual_bayesian": 0.08, "cusum_high": 0.15, "cusum_low": 0.0, "ewma_grade": 0.93, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-10", "blast_id": "TR-3185-10", "timestamp": datetime(2026, 7, 30), "bench": 3185, "tonnage": 48603, "plant_feed_grade": 0.76, "predicted_base_krig": 0.6, "predicted_bayesian": 0.76, "residual_base": 0.16, "residual_bayesian": 0.01, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 0.87, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-11", "blast_id": "TR-3185-11", "timestamp": datetime(2026, 7, 31), "bench": 3185, "tonnage": 45714, "plant_feed_grade": 0.93, "predicted_base_krig": 0.85, "predicted_bayesian": 0.89, "residual_base": 0.07, "residual_bayesian": 0.04, "cusum_high": 0.17, "cusum_low": 0.0, "ewma_grade": 0.87, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-12", "blast_id": "TR-3185-12", "timestamp": datetime(2026, 8, 3), "bench": 3185, "tonnage": 47138, "plant_feed_grade": 0.86, "predicted_base_krig": 0.77, "predicted_bayesian": 0.83, "residual_base": 0.09, "residual_bayesian": 0.03, "cusum_high": 0.14, "cusum_low": 0.0, "ewma_grade": 0.85, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-13", "blast_id": "TR-3185-13", "timestamp": datetime(2026, 8, 7), "bench": 3185, "tonnage": 49752, "plant_feed_grade": 0.72, "predicted_base_krig": 0.64, "predicted_bayesian": 0.68, "residual_base": 0.07, "residual_bayesian": 0.03, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 0.86, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-14", "blast_id": "TR-3185-14", "timestamp": datetime(2026, 8, 10), "bench": 3185, "tonnage": 46120, "plant_feed_grade": 0.63, "predicted_base_krig": 0.54, "predicted_bayesian": 0.59, "residual_base": 0.1, "residual_bayesian": 0.04, "cusum_high": 0.04, "cusum_low": 0.0, "ewma_grade": 0.78, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-15", "blast_id": "TR-3185-15", "timestamp": datetime(2026, 8, 12), "bench": 3185, "tonnage": 45678, "plant_feed_grade": 0.65, "predicted_base_krig": 0.51, "predicted_bayesian": 0.6, "residual_base": 0.14, "residual_bayesian": 0.05, "cusum_high": 0.21, "cusum_low": 0.0, "ewma_grade": 0.85, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-16", "blast_id": "TR-3185-16", "timestamp": datetime(2026, 8, 16), "bench": 3185, "tonnage": 49596, "plant_feed_grade": 0.72, "predicted_base_krig": 0.61, "predicted_bayesian": 0.65, "residual_base": 0.11, "residual_bayesian": 0.07, "cusum_high": 0.16, "cusum_low": 0.0, "ewma_grade": 0.94, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-17", "blast_id": "TR-3185-17", "timestamp": datetime(2026, 8, 20), "bench": 3185, "tonnage": 49911, "plant_feed_grade": 0.8, "predicted_base_krig": 0.65, "predicted_bayesian": 0.76, "residual_base": 0.16, "residual_bayesian": 0.04, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 0.93, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-18", "blast_id": "TR-3185-18", "timestamp": datetime(2026, 8, 23), "bench": 3185, "tonnage": 46812, "plant_feed_grade": 0.9, "predicted_base_krig": 0.78, "predicted_bayesian": 0.87, "residual_base": 0.12, "residual_bayesian": 0.03, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 0.86, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-19", "blast_id": "TR-3185-19", "timestamp": datetime(2026, 8, 24), "bench": 3185, "tonnage": 47510, "plant_feed_grade": 0.9, "predicted_base_krig": 0.84, "predicted_bayesian": 0.87, "residual_base": 0.06, "residual_bayesian": 0.03, "cusum_high": 0.37, "cusum_low": 0.0, "ewma_grade": 0.86, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-20", "blast_id": "TR-3185-20", "timestamp": datetime(2026, 8, 27), "bench": 3185, "tonnage": 49724, "plant_feed_grade": 0.78, "predicted_base_krig": 0.68, "predicted_bayesian": 0.72, "residual_base": 0.1, "residual_bayesian": 0.06, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 0.84, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-21", "blast_id": "TR-3185-21", "timestamp": datetime(2026, 9, 1), "bench": 3185, "tonnage": 46857, "plant_feed_grade": 0.9, "predicted_base_krig": 0.8, "predicted_bayesian": 0.86, "residual_base": 0.11, "residual_bayesian": 0.04, "cusum_high": 0.25, "cusum_low": 0.0, "ewma_grade": 0.83, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-22", "blast_id": "TR-3185-22", "timestamp": datetime(2026, 9, 4), "bench": 3185, "tonnage": 46420, "plant_feed_grade": 0.88, "predicted_base_krig": 0.79, "predicted_bayesian": 0.86, "residual_base": 0.09, "residual_bayesian": 0.02, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 0.86, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-23", "blast_id": "TR-3185-23", "timestamp": datetime(2026, 9, 6), "bench": 3185, "tonnage": 44818, "plant_feed_grade": 0.95, "predicted_base_krig": 0.87, "predicted_bayesian": 0.89, "residual_base": 0.08, "residual_bayesian": 0.06, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 0.88, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-24", "blast_id": "TR-3185-24", "timestamp": datetime(2026, 9, 9), "bench": 3185, "tonnage": 46089, "plant_feed_grade": 0.59, "predicted_base_krig": 0.51, "predicted_bayesian": 0.57, "residual_base": 0.08, "residual_bayesian": 0.02, "cusum_high": 0.07, "cusum_low": 0.0, "ewma_grade": 0.84, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-25", "blast_id": "TR-3185-25", "timestamp": datetime(2026, 9, 12), "bench": 3185, "tonnage": 48778, "plant_feed_grade": 0.81, "predicted_base_krig": 0.71, "predicted_bayesian": 0.81, "residual_base": 0.1, "residual_bayesian": 0.0, "cusum_high": 0.32, "cusum_low": 0.0, "ewma_grade": 0.86, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-26", "blast_id": "TR-3185-26", "timestamp": datetime(2026, 9, 14), "bench": 3185, "tonnage": 46955, "plant_feed_grade": 0.59, "predicted_base_krig": 0.47, "predicted_bayesian": 0.56, "residual_base": 0.12, "residual_bayesian": 0.03, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.85, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-27", "blast_id": "TR-3185-27", "timestamp": datetime(2026, 9, 19), "bench": 3185, "tonnage": 47508, "plant_feed_grade": 0.58, "predicted_base_krig": 0.48, "predicted_bayesian": 0.49, "residual_base": 0.09, "residual_bayesian": 0.08, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.95, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-28", "blast_id": "TR-3185-28", "timestamp": datetime(2026, 9, 20), "bench": 3185, "tonnage": 46843, "plant_feed_grade": 0.68, "predicted_base_krig": 0.58, "predicted_bayesian": 0.66, "residual_base": 0.11, "residual_bayesian": 0.03, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 0.84, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-29", "blast_id": "TR-3185-29", "timestamp": datetime(2026, 9, 24), "bench": 3185, "tonnage": 46085, "plant_feed_grade": 0.65, "predicted_base_krig": 0.54, "predicted_bayesian": 0.6, "residual_base": 0.1, "residual_bayesian": 0.05, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.9, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-30", "blast_id": "TR-3185-30", "timestamp": datetime(2026, 9, 26), "bench": 3185, "tonnage": 47020, "plant_feed_grade": 0.83, "predicted_base_krig": 0.68, "predicted_bayesian": 0.78, "residual_base": 0.15, "residual_bayesian": 0.05, "cusum_high": 0.15, "cusum_low": 0.0, "ewma_grade": 0.79, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-31", "blast_id": "TR-3185-31", "timestamp": datetime(2026, 9, 29), "bench": 3185, "tonnage": 44941, "plant_feed_grade": 0.84, "predicted_base_krig": 0.7, "predicted_bayesian": 0.81, "residual_base": 0.15, "residual_bayesian": 0.04, "cusum_high": 0.06, "cusum_low": 0.0, "ewma_grade": 0.95, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-32", "blast_id": "TR-3185-32", "timestamp": datetime(2026, 10, 4), "bench": 3185, "tonnage": 45416, "plant_feed_grade": 0.88, "predicted_base_krig": 0.76, "predicted_bayesian": 0.85, "residual_base": 0.12, "residual_bayesian": 0.02, "cusum_high": 0.24, "cusum_low": 0.0, "ewma_grade": 0.85, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-33", "blast_id": "TR-3185-33", "timestamp": datetime(2026, 10, 5), "bench": 3185, "tonnage": 48497, "plant_feed_grade": 0.81, "predicted_base_krig": 0.7, "predicted_bayesian": 0.79, "residual_base": 0.12, "residual_bayesian": 0.02, "cusum_high": 0.31, "cusum_low": 0.0, "ewma_grade": 0.87, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-34", "blast_id": "TR-3185-34", "timestamp": datetime(2026, 10, 10), "bench": 3185, "tonnage": 45093, "plant_feed_grade": 0.67, "predicted_base_krig": 0.5, "predicted_bayesian": 0.64, "residual_base": 0.17, "residual_bayesian": 0.03, "cusum_high": 0.07, "cusum_low": 0.0, "ewma_grade": 0.83, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-35", "blast_id": "TR-3185-35", "timestamp": datetime(2026, 10, 11), "bench": 3185, "tonnage": 48735, "plant_feed_grade": 0.75, "predicted_base_krig": 0.6, "predicted_bayesian": 0.75, "residual_base": 0.15, "residual_bayesian": 0.01, "cusum_high": 0.16, "cusum_low": 0.0, "ewma_grade": 0.89, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-36", "blast_id": "TR-3185-36", "timestamp": datetime(2026, 10, 15), "bench": 3185, "tonnage": 47386, "plant_feed_grade": 1.08, "predicted_base_krig": 0.98, "predicted_bayesian": 1.09, "residual_base": 0.1, "residual_bayesian": -0.0, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 0.92, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-37", "blast_id": "TR-3185-37", "timestamp": datetime(2026, 10, 17), "bench": 3185, "tonnage": 49919, "plant_feed_grade": 1.06, "predicted_base_krig": 0.9, "predicted_bayesian": 0.98, "residual_base": 0.16, "residual_bayesian": 0.08, "cusum_high": 0.45, "cusum_low": 0.0, "ewma_grade": 0.9, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-38", "blast_id": "TR-3185-38", "timestamp": datetime(2026, 10, 21), "bench": 3185, "tonnage": 44031, "plant_feed_grade": 0.82, "predicted_base_krig": 0.63, "predicted_bayesian": 0.8, "residual_base": 0.19, "residual_bayesian": 0.02, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 0.86, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-39", "blast_id": "TR-3185-39", "timestamp": datetime(2026, 10, 25), "bench": 3185, "tonnage": 47429, "plant_feed_grade": 0.93, "predicted_base_krig": 0.78, "predicted_bayesian": 0.89, "residual_base": 0.15, "residual_bayesian": 0.04, "cusum_high": 0.35, "cusum_low": 0.0, "ewma_grade": 0.89, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-40", "blast_id": "TR-3185-40", "timestamp": datetime(2026, 10, 27), "bench": 3185, "tonnage": 48243, "plant_feed_grade": 0.71, "predicted_base_krig": 0.61, "predicted_bayesian": 0.68, "residual_base": 0.1, "residual_bayesian": 0.04, "cusum_high": 0.08, "cusum_low": 0.0, "ewma_grade": 0.94, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-41", "blast_id": "TR-3185-41", "timestamp": datetime(2026, 10, 30), "bench": 3185, "tonnage": 44310, "plant_feed_grade": 0.68, "predicted_base_krig": 0.57, "predicted_bayesian": 0.69, "residual_base": 0.11, "residual_bayesian": -0.02, "cusum_high": 0.12, "cusum_low": 0.0, "ewma_grade": 0.77, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-42", "blast_id": "TR-3185-42", "timestamp": datetime(2026, 11, 3), "bench": 3185, "tonnage": 44527, "plant_feed_grade": 1.15, "predicted_base_krig": 1.09, "predicted_bayesian": 1.12, "residual_base": 0.06, "residual_bayesian": 0.03, "cusum_high": 0.42, "cusum_low": 0.0, "ewma_grade": 0.8, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-43", "blast_id": "TR-3185-43", "timestamp": datetime(2026, 11, 4), "bench": 3185, "tonnage": 46093, "plant_feed_grade": 0.93, "predicted_base_krig": 0.85, "predicted_bayesian": 0.84, "residual_base": 0.08, "residual_bayesian": 0.09, "cusum_high": 0.36, "cusum_low": 0.0, "ewma_grade": 0.81, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-44", "blast_id": "TR-3185-44", "timestamp": datetime(2026, 11, 8), "bench": 3185, "tonnage": 49558, "plant_feed_grade": 0.77, "predicted_base_krig": 0.69, "predicted_bayesian": 0.72, "residual_base": 0.07, "residual_bayesian": 0.05, "cusum_high": 0.04, "cusum_low": 0.0, "ewma_grade": 0.79, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-45", "blast_id": "TR-3185-45", "timestamp": datetime(2026, 11, 10), "bench": 3185, "tonnage": 48950, "plant_feed_grade": 0.94, "predicted_base_krig": 0.83, "predicted_bayesian": 0.91, "residual_base": 0.11, "residual_bayesian": 0.02, "cusum_high": 0.35, "cusum_low": 0.0, "ewma_grade": 0.88, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-46", "blast_id": "TR-3185-46", "timestamp": datetime(2026, 11, 15), "bench": 3185, "tonnage": 46354, "plant_feed_grade": 0.89, "predicted_base_krig": 0.84, "predicted_bayesian": 0.87, "residual_base": 0.06, "residual_bayesian": 0.02, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 0.83, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-47", "blast_id": "TR-3185-47", "timestamp": datetime(2026, 11, 16), "bench": 3185, "tonnage": 47464, "plant_feed_grade": 0.89, "predicted_base_krig": 0.79, "predicted_bayesian": 0.8, "residual_base": 0.1, "residual_bayesian": 0.09, "cusum_high": 0.35, "cusum_low": 0.0, "ewma_grade": 0.93, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-48", "blast_id": "TR-3185-48", "timestamp": datetime(2026, 11, 20), "bench": 3185, "tonnage": 44701, "plant_feed_grade": 0.97, "predicted_base_krig": 0.79, "predicted_bayesian": 0.94, "residual_base": 0.19, "residual_bayesian": 0.04, "cusum_high": 0.23, "cusum_low": 0.0, "ewma_grade": 0.89, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-49", "blast_id": "TR-3185-49", "timestamp": datetime(2026, 11, 22), "bench": 3185, "tonnage": 47438, "plant_feed_grade": 0.99, "predicted_base_krig": 0.9, "predicted_bayesian": 0.98, "residual_base": 0.09, "residual_bayesian": 0.01, "cusum_high": 0.18, "cusum_low": 0.0, "ewma_grade": 0.85, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3185-50", "blast_id": "TR-3185-50", "timestamp": datetime(2026, 11, 25), "bench": 3185, "tonnage": 49260, "plant_feed_grade": 0.69, "predicted_base_krig": 0.54, "predicted_bayesian": 0.68, "residual_base": 0.14, "residual_bayesian": 0.01, "cusum_high": 0.01, "cusum_low": 0.0, "ewma_grade": 0.87, "ucl": 1.0, "lcl": 0.45, "target_grade": 0.72},
        {"point_id": "BL-3170-01", "blast_id": "TR-3170-01", "timestamp": datetime(2026, 7, 31), "bench": 3170, "tonnage": 49520, "plant_feed_grade": 0.78, "predicted_base_krig": 0.58, "predicted_bayesian": 0.79, "residual_base": 0.2, "residual_bayesian": -0.02, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 1.13, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-02", "blast_id": "TR-3170-02", "timestamp": datetime(2026, 8, 4), "bench": 3170, "tonnage": 50089, "plant_feed_grade": 1.43, "predicted_base_krig": 1.2, "predicted_bayesian": 1.41, "residual_base": 0.23, "residual_bayesian": 0.03, "cusum_high": 0.24, "cusum_low": 0.0, "ewma_grade": 1.17, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-03", "blast_id": "TR-3170-03", "timestamp": datetime(2026, 8, 8), "bench": 3170, "tonnage": 48607, "plant_feed_grade": 0.99, "predicted_base_krig": 0.75, "predicted_bayesian": 0.96, "residual_base": 0.24, "residual_bayesian": 0.03, "cusum_high": 0.03, "cusum_low": 0.0, "ewma_grade": 1.22, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-04", "blast_id": "TR-3170-04", "timestamp": datetime(2026, 8, 9), "bench": 3170, "tonnage": 50336, "plant_feed_grade": 1.32, "predicted_base_krig": 1.1, "predicted_bayesian": 1.3, "residual_base": 0.21, "residual_bayesian": 0.01, "cusum_high": 0.39, "cusum_low": 0.0, "ewma_grade": 1.13, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-05", "blast_id": "TR-3170-05", "timestamp": datetime(2026, 8, 12), "bench": 3170, "tonnage": 48817, "plant_feed_grade": 1.04, "predicted_base_krig": 0.83, "predicted_bayesian": 1.05, "residual_base": 0.21, "residual_bayesian": -0.01, "cusum_high": 0.0, "cusum_low": 0.0, "ewma_grade": 1.25, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-06", "blast_id": "TR-3170-06", "timestamp": datetime(2026, 8, 15), "bench": 3170, "tonnage": 52537, "plant_feed_grade": 1.12, "predicted_base_krig": 0.89, "predicted_bayesian": 1.08, "residual_base": 0.23, "residual_bayesian": 0.04, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 1.16, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-07", "blast_id": "TR-3170-07", "timestamp": datetime(2026, 8, 18), "bench": 3170, "tonnage": 48016, "plant_feed_grade": 1.64, "predicted_base_krig": 1.43, "predicted_bayesian": 1.6, "residual_base": 0.2, "residual_bayesian": 0.04, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 1.17, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-08", "blast_id": "TR-3170-08", "timestamp": datetime(2026, 8, 22), "bench": 3170, "tonnage": 48117, "plant_feed_grade": 1.0, "predicted_base_krig": 0.73, "predicted_bayesian": 0.98, "residual_base": 0.27, "residual_bayesian": 0.01, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 1.18, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-09", "blast_id": "TR-3170-09", "timestamp": datetime(2026, 8, 24), "bench": 3170, "tonnage": 46489, "plant_feed_grade": 1.21, "predicted_base_krig": 1.01, "predicted_bayesian": 1.19, "residual_base": 0.2, "residual_bayesian": 0.02, "cusum_high": 0.33, "cusum_low": 0.0, "ewma_grade": 1.1, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-10", "blast_id": "TR-3170-10", "timestamp": datetime(2026, 8, 27), "bench": 3170, "tonnage": 53649, "plant_feed_grade": 1.37, "predicted_base_krig": 1.1, "predicted_bayesian": 1.32, "residual_base": 0.28, "residual_bayesian": 0.05, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 1.21, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-11", "blast_id": "TR-3170-11", "timestamp": datetime(2026, 8, 31), "bench": 3170, "tonnage": 47789, "plant_feed_grade": 1.2, "predicted_base_krig": 1.01, "predicted_bayesian": 1.16, "residual_base": 0.19, "residual_bayesian": 0.04, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 1.13, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-12", "blast_id": "TR-3170-12", "timestamp": datetime(2026, 9, 3), "bench": 3170, "tonnage": 45328, "plant_feed_grade": 1.22, "predicted_base_krig": 0.99, "predicted_bayesian": 1.17, "residual_base": 0.22, "residual_bayesian": 0.04, "cusum_high": 0.31, "cusum_low": 0.0, "ewma_grade": 1.15, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-13", "blast_id": "TR-3170-13", "timestamp": datetime(2026, 9, 5), "bench": 3170, "tonnage": 49810, "plant_feed_grade": 0.88, "predicted_base_krig": 0.68, "predicted_bayesian": 0.86, "residual_base": 0.2, "residual_bayesian": 0.03, "cusum_high": 0.01, "cusum_low": 0.0, "ewma_grade": 1.27, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-14", "blast_id": "TR-3170-14", "timestamp": datetime(2026, 9, 9), "bench": 3170, "tonnage": 53515, "plant_feed_grade": 0.97, "predicted_base_krig": 0.75, "predicted_bayesian": 0.94, "residual_base": 0.21, "residual_bayesian": 0.02, "cusum_high": 0.02, "cusum_low": 0.0, "ewma_grade": 1.17, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-15", "blast_id": "TR-3170-15", "timestamp": datetime(2026, 9, 13), "bench": 3170, "tonnage": 45243, "plant_feed_grade": 0.98, "predicted_base_krig": 0.81, "predicted_bayesian": 0.97, "residual_base": 0.17, "residual_bayesian": 0.01, "cusum_high": 0.02, "cusum_low": 0.0, "ewma_grade": 1.24, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-16", "blast_id": "TR-3170-16", "timestamp": datetime(2026, 9, 16), "bench": 3170, "tonnage": 50124, "plant_feed_grade": 1.18, "predicted_base_krig": 0.92, "predicted_bayesian": 1.12, "residual_base": 0.26, "residual_bayesian": 0.06, "cusum_high": 0.24, "cusum_low": 0.0, "ewma_grade": 1.23, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-17", "blast_id": "TR-3170-17", "timestamp": datetime(2026, 9, 19), "bench": 3170, "tonnage": 52701, "plant_feed_grade": 1.12, "predicted_base_krig": 0.89, "predicted_bayesian": 1.1, "residual_base": 0.23, "residual_bayesian": 0.01, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 1.13, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-18", "blast_id": "TR-3170-18", "timestamp": datetime(2026, 9, 20), "bench": 3170, "tonnage": 51623, "plant_feed_grade": 0.88, "predicted_base_krig": 0.63, "predicted_bayesian": 0.85, "residual_base": 0.25, "residual_bayesian": 0.03, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 1.14, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-19", "blast_id": "TR-3170-19", "timestamp": datetime(2026, 9, 25), "bench": 3170, "tonnage": 52356, "plant_feed_grade": 1.24, "predicted_base_krig": 0.98, "predicted_bayesian": 1.23, "residual_base": 0.26, "residual_bayesian": 0.01, "cusum_high": 0.15, "cusum_low": 0.0, "ewma_grade": 1.17, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-20", "blast_id": "TR-3170-20", "timestamp": datetime(2026, 9, 27), "bench": 3170, "tonnage": 48684, "plant_feed_grade": 1.42, "predicted_base_krig": 1.14, "predicted_bayesian": 1.4, "residual_base": 0.27, "residual_bayesian": 0.01, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 1.11, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-21", "blast_id": "TR-3170-21", "timestamp": datetime(2026, 10, 1), "bench": 3170, "tonnage": 53868, "plant_feed_grade": 1.11, "predicted_base_krig": 0.91, "predicted_bayesian": 1.09, "residual_base": 0.21, "residual_bayesian": 0.03, "cusum_high": 0.25, "cusum_low": 0.0, "ewma_grade": 1.13, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-22", "blast_id": "TR-3170-22", "timestamp": datetime(2026, 10, 4), "bench": 3170, "tonnage": 50701, "plant_feed_grade": 1.11, "predicted_base_krig": 0.89, "predicted_bayesian": 1.09, "residual_base": 0.22, "residual_bayesian": 0.02, "cusum_high": 0.07, "cusum_low": 0.0, "ewma_grade": 1.09, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-23", "blast_id": "TR-3170-23", "timestamp": datetime(2026, 10, 5), "bench": 3170, "tonnage": 52403, "plant_feed_grade": 1.0, "predicted_base_krig": 0.84, "predicted_bayesian": 0.99, "residual_base": 0.16, "residual_bayesian": 0.01, "cusum_high": 0.19, "cusum_low": 0.0, "ewma_grade": 1.24, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-24", "blast_id": "TR-3170-24", "timestamp": datetime(2026, 10, 8), "bench": 3170, "tonnage": 51481, "plant_feed_grade": 1.04, "predicted_base_krig": 0.82, "predicted_bayesian": 1.01, "residual_base": 0.22, "residual_bayesian": 0.03, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 1.05, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-25", "blast_id": "TR-3170-25", "timestamp": datetime(2026, 10, 11), "bench": 3170, "tonnage": 46578, "plant_feed_grade": 1.23, "predicted_base_krig": 1.04, "predicted_bayesian": 1.23, "residual_base": 0.19, "residual_bayesian": -0.0, "cusum_high": 0.31, "cusum_low": 0.0, "ewma_grade": 1.23, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-26", "blast_id": "TR-3170-26", "timestamp": datetime(2026, 10, 14), "bench": 3170, "tonnage": 53627, "plant_feed_grade": 1.43, "predicted_base_krig": 1.2, "predicted_bayesian": 1.37, "residual_base": 0.23, "residual_bayesian": 0.07, "cusum_high": 0.19, "cusum_low": 0.0, "ewma_grade": 1.13, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-27", "blast_id": "TR-3170-27", "timestamp": datetime(2026, 10, 17), "bench": 3170, "tonnage": 48201, "plant_feed_grade": 0.92, "predicted_base_krig": 0.72, "predicted_bayesian": 0.86, "residual_base": 0.2, "residual_bayesian": 0.06, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 1.14, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-28", "blast_id": "TR-3170-28", "timestamp": datetime(2026, 10, 20), "bench": 3170, "tonnage": 46215, "plant_feed_grade": 1.28, "predicted_base_krig": 1.06, "predicted_bayesian": 1.26, "residual_base": 0.22, "residual_bayesian": 0.02, "cusum_high": 0.17, "cusum_low": 0.0, "ewma_grade": 1.17, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-29", "blast_id": "TR-3170-29", "timestamp": datetime(2026, 10, 25), "bench": 3170, "tonnage": 53597, "plant_feed_grade": 0.96, "predicted_base_krig": 0.74, "predicted_bayesian": 0.93, "residual_base": 0.22, "residual_bayesian": 0.03, "cusum_high": 0.03, "cusum_low": 0.0, "ewma_grade": 1.19, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-30", "blast_id": "TR-3170-30", "timestamp": datetime(2026, 10, 28), "bench": 3170, "tonnage": 49459, "plant_feed_grade": 1.12, "predicted_base_krig": 0.9, "predicted_bayesian": 1.09, "residual_base": 0.21, "residual_bayesian": 0.03, "cusum_high": 0.19, "cusum_low": 0.0, "ewma_grade": 1.16, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-31", "blast_id": "TR-3170-31", "timestamp": datetime(2026, 10, 29), "bench": 3170, "tonnage": 52266, "plant_feed_grade": 1.04, "predicted_base_krig": 0.81, "predicted_bayesian": 1.0, "residual_base": 0.22, "residual_bayesian": 0.04, "cusum_high": 0.01, "cusum_low": 0.0, "ewma_grade": 1.15, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-32", "blast_id": "TR-3170-32", "timestamp": datetime(2026, 11, 3), "bench": 3170, "tonnage": 52856, "plant_feed_grade": 1.17, "predicted_base_krig": 0.97, "predicted_bayesian": 1.14, "residual_base": 0.2, "residual_bayesian": 0.03, "cusum_high": 0.28, "cusum_low": 0.0, "ewma_grade": 1.11, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-33", "blast_id": "TR-3170-33", "timestamp": datetime(2026, 11, 6), "bench": 3170, "tonnage": 49404, "plant_feed_grade": 1.41, "predicted_base_krig": 1.22, "predicted_bayesian": 1.37, "residual_base": 0.19, "residual_bayesian": 0.04, "cusum_high": 0.36, "cusum_low": 0.0, "ewma_grade": 1.21, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-34", "blast_id": "TR-3170-34", "timestamp": datetime(2026, 11, 8), "bench": 3170, "tonnage": 53994, "plant_feed_grade": 1.21, "predicted_base_krig": 0.97, "predicted_bayesian": 1.18, "residual_base": 0.23, "residual_bayesian": 0.03, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 1.15, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-35", "blast_id": "TR-3170-35", "timestamp": datetime(2026, 11, 12), "bench": 3170, "tonnage": 52758, "plant_feed_grade": 0.99, "predicted_base_krig": 0.8, "predicted_bayesian": 0.95, "residual_base": 0.19, "residual_bayesian": 0.03, "cusum_high": 0.08, "cusum_low": 0.0, "ewma_grade": 1.21, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-36", "blast_id": "TR-3170-36", "timestamp": datetime(2026, 11, 13), "bench": 3170, "tonnage": 50046, "plant_feed_grade": 1.57, "predicted_base_krig": 1.36, "predicted_bayesian": 1.52, "residual_base": 0.21, "residual_bayesian": 0.06, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 1.25, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-37", "blast_id": "TR-3170-37", "timestamp": datetime(2026, 11, 16), "bench": 3170, "tonnage": 47837, "plant_feed_grade": 0.99, "predicted_base_krig": 0.81, "predicted_bayesian": 0.96, "residual_base": 0.18, "residual_bayesian": 0.04, "cusum_high": 0.11, "cusum_low": 0.0, "ewma_grade": 1.19, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-38", "blast_id": "TR-3170-38", "timestamp": datetime(2026, 11, 20), "bench": 3170, "tonnage": 52889, "plant_feed_grade": 1.4, "predicted_base_krig": 1.21, "predicted_bayesian": 1.32, "residual_base": 0.19, "residual_bayesian": 0.08, "cusum_high": 0.16, "cusum_low": 0.0, "ewma_grade": 1.22, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-39", "blast_id": "TR-3170-39", "timestamp": datetime(2026, 11, 22), "bench": 3170, "tonnage": 49318, "plant_feed_grade": 1.19, "predicted_base_krig": 1.01, "predicted_bayesian": 1.15, "residual_base": 0.19, "residual_bayesian": 0.04, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 1.25, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-40", "blast_id": "TR-3170-40", "timestamp": datetime(2026, 11, 25), "bench": 3170, "tonnage": 49702, "plant_feed_grade": 1.06, "predicted_base_krig": 0.79, "predicted_bayesian": 1.02, "residual_base": 0.27, "residual_bayesian": 0.04, "cusum_high": 0.05, "cusum_low": 0.0, "ewma_grade": 1.15, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-41", "blast_id": "TR-3170-41", "timestamp": datetime(2026, 11, 28), "bench": 3170, "tonnage": 47102, "plant_feed_grade": 1.13, "predicted_base_krig": 0.88, "predicted_bayesian": 1.08, "residual_base": 0.24, "residual_bayesian": 0.05, "cusum_high": 0.1, "cusum_low": 0.0, "ewma_grade": 1.13, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-42", "blast_id": "TR-3170-42", "timestamp": datetime(2026, 12, 3), "bench": 3170, "tonnage": 50296, "plant_feed_grade": 1.14, "predicted_base_krig": 0.89, "predicted_bayesian": 1.09, "residual_base": 0.25, "residual_bayesian": 0.04, "cusum_high": 0.28, "cusum_low": 0.0, "ewma_grade": 1.22, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-43", "blast_id": "TR-3170-43", "timestamp": datetime(2026, 12, 6), "bench": 3170, "tonnage": 53920, "plant_feed_grade": 1.17, "predicted_base_krig": 0.97, "predicted_bayesian": 1.12, "residual_base": 0.2, "residual_bayesian": 0.05, "cusum_high": 0.16, "cusum_low": 0.0, "ewma_grade": 1.2, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-44", "blast_id": "TR-3170-44", "timestamp": datetime(2026, 12, 8), "bench": 3170, "tonnage": 45330, "plant_feed_grade": 1.09, "predicted_base_krig": 0.89, "predicted_bayesian": 1.06, "residual_base": 0.2, "residual_bayesian": 0.03, "cusum_high": 0.23, "cusum_low": 0.0, "ewma_grade": 1.15, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-45", "blast_id": "TR-3170-45", "timestamp": datetime(2026, 12, 11), "bench": 3170, "tonnage": 51824, "plant_feed_grade": 1.09, "predicted_base_krig": 0.87, "predicted_bayesian": 1.05, "residual_base": 0.23, "residual_bayesian": 0.04, "cusum_high": 0.29, "cusum_low": 0.0, "ewma_grade": 1.12, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-46", "blast_id": "TR-3170-46", "timestamp": datetime(2026, 12, 14), "bench": 3170, "tonnage": 45313, "plant_feed_grade": 1.16, "predicted_base_krig": 0.97, "predicted_bayesian": 1.16, "residual_base": 0.19, "residual_bayesian": 0.0, "cusum_high": 0.29, "cusum_low": 0.0, "ewma_grade": 1.21, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-47", "blast_id": "TR-3170-47", "timestamp": datetime(2026, 12, 17), "bench": 3170, "tonnage": 45399, "plant_feed_grade": 0.78, "predicted_base_krig": 0.53, "predicted_bayesian": 0.74, "residual_base": 0.25, "residual_bayesian": 0.03, "cusum_high": 0.1, "cusum_low": 0.0, "ewma_grade": 1.09, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-48", "blast_id": "TR-3170-48", "timestamp": datetime(2026, 12, 21), "bench": 3170, "tonnage": 48676, "plant_feed_grade": 1.28, "predicted_base_krig": 1.09, "predicted_bayesian": 1.23, "residual_base": 0.19, "residual_bayesian": 0.05, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 1.19, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-49", "blast_id": "TR-3170-49", "timestamp": datetime(2026, 12, 22), "bench": 3170, "tonnage": 45985, "plant_feed_grade": 1.14, "predicted_base_krig": 0.92, "predicted_bayesian": 1.12, "residual_base": 0.22, "residual_bayesian": 0.02, "cusum_high": 0.32, "cusum_low": 0.0, "ewma_grade": 1.18, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3170-50", "blast_id": "TR-3170-50", "timestamp": datetime(2026, 12, 25), "bench": 3170, "tonnage": 49894, "plant_feed_grade": 1.34, "predicted_base_krig": 1.12, "predicted_bayesian": 1.35, "residual_base": 0.22, "residual_bayesian": -0.01, "cusum_high": 0.2, "cusum_low": 0.0, "ewma_grade": 1.22, "ucl": 1.3, "lcl": 0.85, "target_grade": 1.1},
        {"point_id": "BL-3155-01", "blast_id": "TR-3155-01", "timestamp": datetime(2026, 6, 1), "bench": 3155, "tonnage": 58203, "plant_feed_grade": 1.55, "predicted_base_krig": 1.3, "predicted_bayesian": 1.53, "residual_base": 0.25, "residual_bayesian": 0.02, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 1.52, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-02", "blast_id": "TR-3155-02", "timestamp": datetime(2026, 6, 4), "bench": 3155, "tonnage": 58767, "plant_feed_grade": 1.56, "predicted_base_krig": 1.28, "predicted_bayesian": 1.53, "residual_base": 0.28, "residual_bayesian": 0.04, "cusum_high": 0.14, "cusum_low": 0.0, "ewma_grade": 1.49, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-03", "blast_id": "TR-3155-03", "timestamp": datetime(2026, 6, 8), "bench": 3155, "tonnage": 53964, "plant_feed_grade": 1.47, "predicted_base_krig": 1.21, "predicted_bayesian": 1.45, "residual_base": 0.26, "residual_bayesian": 0.02, "cusum_high": 0.33, "cusum_low": 0.0, "ewma_grade": 1.46, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-04", "blast_id": "TR-3155-04", "timestamp": datetime(2026, 6, 10), "bench": 3155, "tonnage": 58887, "plant_feed_grade": 1.45, "predicted_base_krig": 1.19, "predicted_bayesian": 1.43, "residual_base": 0.26, "residual_bayesian": 0.02, "cusum_high": 0.11, "cusum_low": 0.0, "ewma_grade": 1.43, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-05", "blast_id": "TR-3155-05", "timestamp": datetime(2026, 6, 15), "bench": 3155, "tonnage": 55352, "plant_feed_grade": 1.46, "predicted_base_krig": 1.2, "predicted_bayesian": 1.44, "residual_base": 0.25, "residual_bayesian": 0.02, "cusum_high": 0.36, "cusum_low": 0.0, "ewma_grade": 1.49, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-06", "blast_id": "TR-3155-06", "timestamp": datetime(2026, 6, 17), "bench": 3155, "tonnage": 53404, "plant_feed_grade": 1.41, "predicted_base_krig": 1.16, "predicted_bayesian": 1.39, "residual_base": 0.25, "residual_bayesian": 0.02, "cusum_high": 0.2, "cusum_low": 0.0, "ewma_grade": 1.45, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-07", "blast_id": "TR-3155-07", "timestamp": datetime(2026, 6, 19), "bench": 3155, "tonnage": 55301, "plant_feed_grade": 1.38, "predicted_base_krig": 1.18, "predicted_bayesian": 1.36, "residual_base": 0.2, "residual_bayesian": 0.02, "cusum_high": 0.05, "cusum_low": 0.0, "ewma_grade": 1.59, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-08", "blast_id": "TR-3155-08", "timestamp": datetime(2026, 6, 23), "bench": 3155, "tonnage": 55675, "plant_feed_grade": 1.47, "predicted_base_krig": 1.15, "predicted_bayesian": 1.45, "residual_base": 0.32, "residual_bayesian": 0.03, "cusum_high": 0.23, "cusum_low": 0.0, "ewma_grade": 1.55, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-09", "blast_id": "TR-3155-09", "timestamp": datetime(2026, 6, 27), "bench": 3155, "tonnage": 58039, "plant_feed_grade": 1.52, "predicted_base_krig": 1.29, "predicted_bayesian": 1.47, "residual_base": 0.23, "residual_bayesian": 0.05, "cusum_high": 0.31, "cusum_low": 0.0, "ewma_grade": 1.54, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-10", "blast_id": "TR-3155-10", "timestamp": datetime(2026, 6, 30), "bench": 3155, "tonnage": 55518, "plant_feed_grade": 1.24, "predicted_base_krig": 1.01, "predicted_bayesian": 1.22, "residual_base": 0.23, "residual_bayesian": 0.03, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 1.5, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-11", "blast_id": "TR-3155-11", "timestamp": datetime(2026, 7, 2), "bench": 3155, "tonnage": 57346, "plant_feed_grade": 1.43, "predicted_base_krig": 1.22, "predicted_bayesian": 1.37, "residual_base": 0.21, "residual_bayesian": 0.06, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 1.44, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-12", "blast_id": "TR-3155-12", "timestamp": datetime(2026, 7, 5), "bench": 3155, "tonnage": 55839, "plant_feed_grade": 1.51, "predicted_base_krig": 1.25, "predicted_bayesian": 1.49, "residual_base": 0.27, "residual_bayesian": 0.02, "cusum_high": 0.17, "cusum_low": 0.0, "ewma_grade": 1.48, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-13", "blast_id": "TR-3155-13", "timestamp": datetime(2026, 7, 8), "bench": 3155, "tonnage": 58805, "plant_feed_grade": 1.83, "predicted_base_krig": 1.49, "predicted_bayesian": 1.8, "residual_base": 0.33, "residual_bayesian": 0.03, "cusum_high": 0.4, "cusum_low": 0.0, "ewma_grade": 1.49, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-14", "blast_id": "TR-3155-14", "timestamp": datetime(2026, 7, 11), "bench": 3155, "tonnage": 53964, "plant_feed_grade": 1.21, "predicted_base_krig": 0.97, "predicted_bayesian": 1.15, "residual_base": 0.24, "residual_bayesian": 0.07, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 1.52, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-15", "blast_id": "TR-3155-15", "timestamp": datetime(2026, 7, 14), "bench": 3155, "tonnage": 53069, "plant_feed_grade": 1.67, "predicted_base_krig": 1.39, "predicted_bayesian": 1.62, "residual_base": 0.28, "residual_bayesian": 0.05, "cusum_high": 0.39, "cusum_low": 0.0, "ewma_grade": 1.41, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-16", "blast_id": "TR-3155-16", "timestamp": datetime(2026, 7, 17), "bench": 3155, "tonnage": 57542, "plant_feed_grade": 1.57, "predicted_base_krig": 1.3, "predicted_bayesian": 1.54, "residual_base": 0.26, "residual_bayesian": 0.02, "cusum_high": 0.41, "cusum_low": 0.0, "ewma_grade": 1.56, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-17", "blast_id": "TR-3155-17", "timestamp": datetime(2026, 7, 19), "bench": 3155, "tonnage": 55894, "plant_feed_grade": 1.69, "predicted_base_krig": 1.45, "predicted_bayesian": 1.64, "residual_base": 0.23, "residual_bayesian": 0.05, "cusum_high": 0.36, "cusum_low": 0.0, "ewma_grade": 1.5, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-18", "blast_id": "TR-3155-18", "timestamp": datetime(2026, 7, 23), "bench": 3155, "tonnage": 53471, "plant_feed_grade": 1.32, "predicted_base_krig": 1.07, "predicted_bayesian": 1.28, "residual_base": 0.26, "residual_bayesian": 0.05, "cusum_high": 0.11, "cusum_low": 0.0, "ewma_grade": 1.5, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-19", "blast_id": "TR-3155-19", "timestamp": datetime(2026, 7, 25), "bench": 3155, "tonnage": 58709, "plant_feed_grade": 1.68, "predicted_base_krig": 1.44, "predicted_bayesian": 1.65, "residual_base": 0.24, "residual_bayesian": 0.04, "cusum_high": 0.4, "cusum_low": 0.0, "ewma_grade": 1.49, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-20", "blast_id": "TR-3155-20", "timestamp": datetime(2026, 7, 29), "bench": 3155, "tonnage": 57284, "plant_feed_grade": 1.51, "predicted_base_krig": 1.23, "predicted_bayesian": 1.49, "residual_base": 0.28, "residual_bayesian": 0.03, "cusum_high": 0.34, "cusum_low": 0.0, "ewma_grade": 1.52, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-21", "blast_id": "TR-3155-21", "timestamp": datetime(2026, 8, 1), "bench": 3155, "tonnage": 56584, "plant_feed_grade": 1.43, "predicted_base_krig": 1.25, "predicted_bayesian": 1.41, "residual_base": 0.19, "residual_bayesian": 0.03, "cusum_high": 0.2, "cusum_low": 0.0, "ewma_grade": 1.6, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-22", "blast_id": "TR-3155-22", "timestamp": datetime(2026, 8, 5), "bench": 3155, "tonnage": 53362, "plant_feed_grade": 1.58, "predicted_base_krig": 1.39, "predicted_bayesian": 1.53, "residual_base": 0.19, "residual_bayesian": 0.05, "cusum_high": 0.34, "cusum_low": 0.0, "ewma_grade": 1.51, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-23", "blast_id": "TR-3155-23", "timestamp": datetime(2026, 8, 6), "bench": 3155, "tonnage": 57465, "plant_feed_grade": 1.97, "predicted_base_krig": 1.7, "predicted_bayesian": 1.93, "residual_base": 0.27, "residual_bayesian": 0.05, "cusum_high": 0.57, "cusum_low": 0.0, "ewma_grade": 1.4, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-24", "blast_id": "TR-3155-24", "timestamp": datetime(2026, 8, 9), "bench": 3155, "tonnage": 54370, "plant_feed_grade": 1.5, "predicted_base_krig": 1.3, "predicted_bayesian": 1.49, "residual_base": 0.2, "residual_bayesian": 0.01, "cusum_high": 0.25, "cusum_low": 0.0, "ewma_grade": 1.52, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-25", "blast_id": "TR-3155-25", "timestamp": datetime(2026, 8, 14), "bench": 3155, "tonnage": 54221, "plant_feed_grade": 1.46, "predicted_base_krig": 1.18, "predicted_bayesian": 1.42, "residual_base": 0.28, "residual_bayesian": 0.05, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 1.43, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-26", "blast_id": "TR-3155-26", "timestamp": datetime(2026, 8, 16), "bench": 3155, "tonnage": 55075, "plant_feed_grade": 1.58, "predicted_base_krig": 1.34, "predicted_bayesian": 1.53, "residual_base": 0.24, "residual_bayesian": 0.05, "cusum_high": 0.44, "cusum_low": 0.0, "ewma_grade": 1.58, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-27", "blast_id": "TR-3155-27", "timestamp": datetime(2026, 8, 19), "bench": 3155, "tonnage": 58240, "plant_feed_grade": 1.19, "predicted_base_krig": 0.99, "predicted_bayesian": 1.15, "residual_base": 0.2, "residual_bayesian": 0.04, "cusum_high": 0.18, "cusum_low": 0.0, "ewma_grade": 1.59, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-28", "blast_id": "TR-3155-28", "timestamp": datetime(2026, 8, 21), "bench": 3155, "tonnage": 58015, "plant_feed_grade": 1.32, "predicted_base_krig": 1.02, "predicted_bayesian": 1.27, "residual_base": 0.3, "residual_bayesian": 0.05, "cusum_high": 0.05, "cusum_low": 0.0, "ewma_grade": 1.39, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-29", "blast_id": "TR-3155-29", "timestamp": datetime(2026, 8, 26), "bench": 3155, "tonnage": 58828, "plant_feed_grade": 1.6, "predicted_base_krig": 1.35, "predicted_bayesian": 1.55, "residual_base": 0.25, "residual_bayesian": 0.05, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 1.47, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-30", "blast_id": "TR-3155-30", "timestamp": datetime(2026, 8, 29), "bench": 3155, "tonnage": 56557, "plant_feed_grade": 1.48, "predicted_base_krig": 1.2, "predicted_bayesian": 1.43, "residual_base": 0.28, "residual_bayesian": 0.04, "cusum_high": 0.2, "cusum_low": 0.0, "ewma_grade": 1.46, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-31", "blast_id": "TR-3155-31", "timestamp": datetime(2026, 8, 30), "bench": 3155, "tonnage": 54548, "plant_feed_grade": 1.27, "predicted_base_krig": 1.02, "predicted_bayesian": 1.24, "residual_base": 0.25, "residual_bayesian": 0.03, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 1.5, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-32", "blast_id": "TR-3155-32", "timestamp": datetime(2026, 9, 3), "bench": 3155, "tonnage": 54408, "plant_feed_grade": 1.84, "predicted_base_krig": 1.63, "predicted_bayesian": 1.78, "residual_base": 0.21, "residual_bayesian": 0.07, "cusum_high": 0.29, "cusum_low": 0.0, "ewma_grade": 1.47, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-33", "blast_id": "TR-3155-33", "timestamp": datetime(2026, 9, 7), "bench": 3155, "tonnage": 55585, "plant_feed_grade": 1.52, "predicted_base_krig": 1.22, "predicted_bayesian": 1.5, "residual_base": 0.3, "residual_bayesian": 0.02, "cusum_high": 0.39, "cusum_low": 0.0, "ewma_grade": 1.48, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-34", "blast_id": "TR-3155-34", "timestamp": datetime(2026, 9, 8), "bench": 3155, "tonnage": 55140, "plant_feed_grade": 1.35, "predicted_base_krig": 1.05, "predicted_bayesian": 1.34, "residual_base": 0.3, "residual_bayesian": 0.01, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 1.42, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-35", "blast_id": "TR-3155-35", "timestamp": datetime(2026, 9, 12), "bench": 3155, "tonnage": 56239, "plant_feed_grade": 1.41, "predicted_base_krig": 1.2, "predicted_bayesian": 1.37, "residual_base": 0.21, "residual_bayesian": 0.04, "cusum_high": 0.35, "cusum_low": 0.0, "ewma_grade": 1.55, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-36", "blast_id": "TR-3155-36", "timestamp": datetime(2026, 9, 14), "bench": 3155, "tonnage": 54348, "plant_feed_grade": 1.44, "predicted_base_krig": 1.16, "predicted_bayesian": 1.4, "residual_base": 0.27, "residual_bayesian": 0.04, "cusum_high": 0.35, "cusum_low": 0.0, "ewma_grade": 1.48, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-37", "blast_id": "TR-3155-37", "timestamp": datetime(2026, 9, 19), "bench": 3155, "tonnage": 55728, "plant_feed_grade": 1.52, "predicted_base_krig": 1.2, "predicted_bayesian": 1.49, "residual_base": 0.32, "residual_bayesian": 0.02, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 1.52, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-38", "blast_id": "TR-3155-38", "timestamp": datetime(2026, 9, 22), "bench": 3155, "tonnage": 54130, "plant_feed_grade": 1.59, "predicted_base_krig": 1.26, "predicted_bayesian": 1.53, "residual_base": 0.32, "residual_bayesian": 0.05, "cusum_high": 0.34, "cusum_low": 0.0, "ewma_grade": 1.53, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-39", "blast_id": "TR-3155-39", "timestamp": datetime(2026, 9, 24), "bench": 3155, "tonnage": 58028, "plant_feed_grade": 1.71, "predicted_base_krig": 1.45, "predicted_bayesian": 1.69, "residual_base": 0.26, "residual_bayesian": 0.03, "cusum_high": 0.32, "cusum_low": 0.0, "ewma_grade": 1.45, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-40", "blast_id": "TR-3155-40", "timestamp": datetime(2026, 9, 26), "bench": 3155, "tonnage": 57773, "plant_feed_grade": 1.54, "predicted_base_krig": 1.28, "predicted_bayesian": 1.49, "residual_base": 0.25, "residual_bayesian": 0.05, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 1.51, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-41", "blast_id": "TR-3155-41", "timestamp": datetime(2026, 10, 1), "bench": 3155, "tonnage": 56629, "plant_feed_grade": 1.67, "predicted_base_krig": 1.46, "predicted_bayesian": 1.61, "residual_base": 0.21, "residual_bayesian": 0.06, "cusum_high": 0.48, "cusum_low": 0.0, "ewma_grade": 1.48, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-42", "blast_id": "TR-3155-42", "timestamp": datetime(2026, 10, 3), "bench": 3155, "tonnage": 57430, "plant_feed_grade": 1.7, "predicted_base_krig": 1.43, "predicted_bayesian": 1.67, "residual_base": 0.27, "residual_bayesian": 0.03, "cusum_high": 0.32, "cusum_low": 0.0, "ewma_grade": 1.57, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-43", "blast_id": "TR-3155-43", "timestamp": datetime(2026, 10, 7), "bench": 3155, "tonnage": 57786, "plant_feed_grade": 1.74, "predicted_base_krig": 1.44, "predicted_bayesian": 1.71, "residual_base": 0.3, "residual_bayesian": 0.03, "cusum_high": 0.48, "cusum_low": 0.0, "ewma_grade": 1.54, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-44", "blast_id": "TR-3155-44", "timestamp": datetime(2026, 10, 9), "bench": 3155, "tonnage": 56781, "plant_feed_grade": 1.21, "predicted_base_krig": 0.92, "predicted_bayesian": 1.14, "residual_base": 0.29, "residual_bayesian": 0.07, "cusum_high": 0.07, "cusum_low": 0.0, "ewma_grade": 1.56, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-45", "blast_id": "TR-3155-45", "timestamp": datetime(2026, 10, 12), "bench": 3155, "tonnage": 55239, "plant_feed_grade": 1.32, "predicted_base_krig": 1.11, "predicted_bayesian": 1.25, "residual_base": 0.21, "residual_bayesian": 0.07, "cusum_high": 0.03, "cusum_low": 0.0, "ewma_grade": 1.48, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-46", "blast_id": "TR-3155-46", "timestamp": datetime(2026, 10, 15), "bench": 3155, "tonnage": 55278, "plant_feed_grade": 1.83, "predicted_base_krig": 1.6, "predicted_bayesian": 1.77, "residual_base": 0.23, "residual_bayesian": 0.05, "cusum_high": 0.55, "cusum_low": 0.0, "ewma_grade": 1.61, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-47", "blast_id": "TR-3155-47", "timestamp": datetime(2026, 10, 19), "bench": 3155, "tonnage": 55366, "plant_feed_grade": 1.52, "predicted_base_krig": 1.22, "predicted_bayesian": 1.47, "residual_base": 0.3, "residual_bayesian": 0.04, "cusum_high": 0.35, "cusum_low": 0.0, "ewma_grade": 1.42, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-48", "blast_id": "TR-3155-48", "timestamp": datetime(2026, 10, 20), "bench": 3155, "tonnage": 53608, "plant_feed_grade": 1.45, "predicted_base_krig": 1.2, "predicted_bayesian": 1.41, "residual_base": 0.25, "residual_bayesian": 0.04, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 1.53, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-49", "blast_id": "TR-3155-49", "timestamp": datetime(2026, 10, 24), "bench": 3155, "tonnage": 56485, "plant_feed_grade": 1.91, "predicted_base_krig": 1.66, "predicted_bayesian": 1.87, "residual_base": 0.25, "residual_bayesian": 0.04, "cusum_high": 0.49, "cusum_low": 0.0, "ewma_grade": 1.54, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3155-50", "blast_id": "TR-3155-50", "timestamp": datetime(2026, 10, 28), "bench": 3155, "tonnage": 54086, "plant_feed_grade": 1.3, "predicted_base_krig": 1.07, "predicted_bayesian": 1.24, "residual_base": 0.23, "residual_bayesian": 0.06, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 1.49, "ucl": 1.55, "lcl": 1.05, "target_grade": 1.3},
        {"point_id": "BL-3140-01", "blast_id": "TR-3140-01", "timestamp": datetime(2026, 5, 3), "bench": 3140, "tonnage": 48926, "plant_feed_grade": 1.11, "predicted_base_krig": 0.93, "predicted_bayesian": 1.08, "residual_base": 0.18, "residual_bayesian": 0.03, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 1.17, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-02", "blast_id": "TR-3140-02", "timestamp": datetime(2026, 5, 6), "bench": 3140, "tonnage": 51008, "plant_feed_grade": 1.11, "predicted_base_krig": 0.91, "predicted_bayesian": 1.07, "residual_base": 0.2, "residual_bayesian": 0.04, "cusum_high": 0.18, "cusum_low": 0.0, "ewma_grade": 1.21, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-03", "blast_id": "TR-3140-03", "timestamp": datetime(2026, 5, 9), "bench": 3140, "tonnage": 49803, "plant_feed_grade": 1.41, "predicted_base_krig": 1.22, "predicted_bayesian": 1.34, "residual_base": 0.19, "residual_bayesian": 0.07, "cusum_high": 0.45, "cusum_low": 0.0, "ewma_grade": 1.22, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-04", "blast_id": "TR-3140-04", "timestamp": datetime(2026, 5, 13), "bench": 3140, "tonnage": 52113, "plant_feed_grade": 1.0, "predicted_base_krig": 0.78, "predicted_bayesian": 0.94, "residual_base": 0.22, "residual_bayesian": 0.06, "cusum_high": 0.18, "cusum_low": 0.0, "ewma_grade": 1.24, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-05", "blast_id": "TR-3140-05", "timestamp": datetime(2026, 5, 16), "bench": 3140, "tonnage": 48840, "plant_feed_grade": 1.24, "predicted_base_krig": 1.01, "predicted_bayesian": 1.23, "residual_base": 0.22, "residual_bayesian": 0.01, "cusum_high": 0.35, "cusum_low": 0.0, "ewma_grade": 1.14, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-06", "blast_id": "TR-3140-06", "timestamp": datetime(2026, 5, 19), "bench": 3140, "tonnage": 49151, "plant_feed_grade": 1.59, "predicted_base_krig": 1.34, "predicted_bayesian": 1.53, "residual_base": 0.26, "residual_bayesian": 0.06, "cusum_high": 0.44, "cusum_low": 0.0, "ewma_grade": 1.15, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-07", "blast_id": "TR-3140-07", "timestamp": datetime(2026, 5, 22), "bench": 3140, "tonnage": 52938, "plant_feed_grade": 1.11, "predicted_base_krig": 0.87, "predicted_bayesian": 1.06, "residual_base": 0.24, "residual_bayesian": 0.05, "cusum_high": 0.21, "cusum_low": 0.0, "ewma_grade": 1.33, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-08", "blast_id": "TR-3140-08", "timestamp": datetime(2026, 5, 24), "bench": 3140, "tonnage": 48079, "plant_feed_grade": 1.1, "predicted_base_krig": 0.96, "predicted_bayesian": 1.09, "residual_base": 0.14, "residual_bayesian": 0.02, "cusum_high": 0.06, "cusum_low": 0.0, "ewma_grade": 1.18, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-09", "blast_id": "TR-3140-09", "timestamp": datetime(2026, 5, 26), "bench": 3140, "tonnage": 48428, "plant_feed_grade": 1.29, "predicted_base_krig": 1.14, "predicted_bayesian": 1.23, "residual_base": 0.15, "residual_bayesian": 0.06, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 1.19, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-10", "blast_id": "TR-3140-10", "timestamp": datetime(2026, 5, 30), "bench": 3140, "tonnage": 50212, "plant_feed_grade": 0.93, "predicted_base_krig": 0.69, "predicted_bayesian": 0.9, "residual_base": 0.24, "residual_bayesian": 0.03, "cusum_high": 0.14, "cusum_low": 0.0, "ewma_grade": 1.12, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-11", "blast_id": "TR-3140-11", "timestamp": datetime(2026, 6, 1), "bench": 3140, "tonnage": 51400, "plant_feed_grade": 1.23, "predicted_base_krig": 1.01, "predicted_bayesian": 1.19, "residual_base": 0.22, "residual_bayesian": 0.04, "cusum_high": 0.23, "cusum_low": 0.0, "ewma_grade": 1.12, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-12", "blast_id": "TR-3140-12", "timestamp": datetime(2026, 6, 5), "bench": 3140, "tonnage": 49667, "plant_feed_grade": 0.96, "predicted_base_krig": 0.72, "predicted_bayesian": 0.91, "residual_base": 0.24, "residual_bayesian": 0.05, "cusum_high": 0.12, "cusum_low": 0.0, "ewma_grade": 1.21, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-13", "blast_id": "TR-3140-13", "timestamp": datetime(2026, 6, 7), "bench": 3140, "tonnage": 50251, "plant_feed_grade": 1.04, "predicted_base_krig": 0.86, "predicted_bayesian": 0.97, "residual_base": 0.18, "residual_bayesian": 0.07, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 1.2, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-14", "blast_id": "TR-3140-14", "timestamp": datetime(2026, 6, 11), "bench": 3140, "tonnage": 52870, "plant_feed_grade": 1.2, "predicted_base_krig": 1.01, "predicted_bayesian": 1.13, "residual_base": 0.19, "residual_bayesian": 0.07, "cusum_high": 0.37, "cusum_low": 0.0, "ewma_grade": 1.19, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-15", "blast_id": "TR-3140-15", "timestamp": datetime(2026, 6, 14), "bench": 3140, "tonnage": 51117, "plant_feed_grade": 1.21, "predicted_base_krig": 1.04, "predicted_bayesian": 1.16, "residual_base": 0.18, "residual_bayesian": 0.05, "cusum_high": 0.32, "cusum_low": 0.0, "ewma_grade": 1.26, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-16", "blast_id": "TR-3140-16", "timestamp": datetime(2026, 6, 16), "bench": 3140, "tonnage": 48315, "plant_feed_grade": 1.25, "predicted_base_krig": 1.08, "predicted_bayesian": 1.17, "residual_base": 0.17, "residual_bayesian": 0.07, "cusum_high": 0.17, "cusum_low": 0.0, "ewma_grade": 1.2, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-17", "blast_id": "TR-3140-17", "timestamp": datetime(2026, 6, 21), "bench": 3140, "tonnage": 50548, "plant_feed_grade": 1.01, "predicted_base_krig": 0.77, "predicted_bayesian": 0.94, "residual_base": 0.25, "residual_bayesian": 0.07, "cusum_high": 0.1, "cusum_low": 0.0, "ewma_grade": 1.16, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-18", "blast_id": "TR-3140-18", "timestamp": datetime(2026, 6, 23), "bench": 3140, "tonnage": 50484, "plant_feed_grade": 1.54, "predicted_base_krig": 1.31, "predicted_bayesian": 1.51, "residual_base": 0.23, "residual_bayesian": 0.03, "cusum_high": 0.42, "cusum_low": 0.0, "ewma_grade": 1.2, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-19", "blast_id": "TR-3140-19", "timestamp": datetime(2026, 6, 26), "bench": 3140, "tonnage": 51139, "plant_feed_grade": 1.2, "predicted_base_krig": 0.93, "predicted_bayesian": 1.17, "residual_base": 0.27, "residual_bayesian": 0.03, "cusum_high": 0.34, "cusum_low": 0.0, "ewma_grade": 1.09, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-20", "blast_id": "TR-3140-20", "timestamp": datetime(2026, 6, 28), "bench": 3140, "tonnage": 48404, "plant_feed_grade": 1.24, "predicted_base_krig": 1.05, "predicted_bayesian": 1.18, "residual_base": 0.19, "residual_bayesian": 0.06, "cusum_high": 0.1, "cusum_low": 0.0, "ewma_grade": 1.25, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-21", "blast_id": "TR-3140-21", "timestamp": datetime(2026, 7, 2), "bench": 3140, "tonnage": 52663, "plant_feed_grade": 1.13, "predicted_base_krig": 0.91, "predicted_bayesian": 1.08, "residual_base": 0.22, "residual_bayesian": 0.05, "cusum_high": 0.08, "cusum_low": 0.0, "ewma_grade": 1.23, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-22", "blast_id": "TR-3140-22", "timestamp": datetime(2026, 7, 4), "bench": 3140, "tonnage": 50512, "plant_feed_grade": 1.59, "predicted_base_krig": 1.39, "predicted_bayesian": 1.53, "residual_base": 0.21, "residual_bayesian": 0.06, "cusum_high": 0.52, "cusum_low": 0.0, "ewma_grade": 1.23, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-23", "blast_id": "TR-3140-23", "timestamp": datetime(2026, 7, 7), "bench": 3140, "tonnage": 49162, "plant_feed_grade": 1.07, "predicted_base_krig": 0.88, "predicted_bayesian": 1.04, "residual_base": 0.19, "residual_bayesian": 0.03, "cusum_high": 0.18, "cusum_low": 0.0, "ewma_grade": 1.03, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-24", "blast_id": "TR-3140-24", "timestamp": datetime(2026, 7, 12), "bench": 3140, "tonnage": 50197, "plant_feed_grade": 1.19, "predicted_base_krig": 1.0, "predicted_bayesian": 1.14, "residual_base": 0.19, "residual_bayesian": 0.05, "cusum_high": 0.26, "cusum_low": 0.0, "ewma_grade": 1.1, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-25", "blast_id": "TR-3140-25", "timestamp": datetime(2026, 7, 15), "bench": 3140, "tonnage": 48306, "plant_feed_grade": 1.29, "predicted_base_krig": 1.05, "predicted_bayesian": 1.22, "residual_base": 0.24, "residual_bayesian": 0.07, "cusum_high": 0.18, "cusum_low": 0.0, "ewma_grade": 1.22, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-26", "blast_id": "TR-3140-26", "timestamp": datetime(2026, 7, 18), "bench": 3140, "tonnage": 49486, "plant_feed_grade": 1.19, "predicted_base_krig": 0.94, "predicted_bayesian": 1.15, "residual_base": 0.24, "residual_bayesian": 0.04, "cusum_high": 0.14, "cusum_low": 0.0, "ewma_grade": 1.27, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-27", "blast_id": "TR-3140-27", "timestamp": datetime(2026, 7, 21), "bench": 3140, "tonnage": 50547, "plant_feed_grade": 1.1, "predicted_base_krig": 0.89, "predicted_bayesian": 1.04, "residual_base": 0.21, "residual_bayesian": 0.06, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 1.21, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-28", "blast_id": "TR-3140-28", "timestamp": datetime(2026, 7, 23), "bench": 3140, "tonnage": 52240, "plant_feed_grade": 1.08, "predicted_base_krig": 0.86, "predicted_bayesian": 1.04, "residual_base": 0.22, "residual_bayesian": 0.04, "cusum_high": 0.06, "cusum_low": 0.0, "ewma_grade": 1.15, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-29", "blast_id": "TR-3140-29", "timestamp": datetime(2026, 7, 26), "bench": 3140, "tonnage": 50070, "plant_feed_grade": 1.18, "predicted_base_krig": 1.01, "predicted_bayesian": 1.12, "residual_base": 0.17, "residual_bayesian": 0.06, "cusum_high": 0.12, "cusum_low": 0.0, "ewma_grade": 1.14, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-30", "blast_id": "TR-3140-30", "timestamp": datetime(2026, 7, 29), "bench": 3140, "tonnage": 50092, "plant_feed_grade": 1.27, "predicted_base_krig": 1.06, "predicted_bayesian": 1.21, "residual_base": 0.2, "residual_bayesian": 0.06, "cusum_high": 0.19, "cusum_low": 0.0, "ewma_grade": 1.18, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-31", "blast_id": "TR-3140-31", "timestamp": datetime(2026, 8, 1), "bench": 3140, "tonnage": 48060, "plant_feed_grade": 1.11, "predicted_base_krig": 0.92, "predicted_bayesian": 1.03, "residual_base": 0.19, "residual_bayesian": 0.08, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 1.21, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-32", "blast_id": "TR-3140-32", "timestamp": datetime(2026, 8, 5), "bench": 3140, "tonnage": 50496, "plant_feed_grade": 1.18, "predicted_base_krig": 0.97, "predicted_bayesian": 1.15, "residual_base": 0.21, "residual_bayesian": 0.03, "cusum_high": 0.11, "cusum_low": 0.0, "ewma_grade": 1.13, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-33", "blast_id": "TR-3140-33", "timestamp": datetime(2026, 8, 7), "bench": 3140, "tonnage": 52297, "plant_feed_grade": 1.32, "predicted_base_krig": 1.08, "predicted_bayesian": 1.28, "residual_base": 0.24, "residual_bayesian": 0.04, "cusum_high": 0.37, "cusum_low": 0.0, "ewma_grade": 1.26, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-34", "blast_id": "TR-3140-34", "timestamp": datetime(2026, 8, 10), "bench": 3140, "tonnage": 49273, "plant_feed_grade": 1.09, "predicted_base_krig": 0.92, "predicted_bayesian": 1.03, "residual_base": 0.17, "residual_bayesian": 0.06, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 1.29, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-35", "blast_id": "TR-3140-35", "timestamp": datetime(2026, 8, 13), "bench": 3140, "tonnage": 49931, "plant_feed_grade": 1.33, "predicted_base_krig": 1.11, "predicted_bayesian": 1.28, "residual_base": 0.22, "residual_bayesian": 0.05, "cusum_high": 0.33, "cusum_low": 0.0, "ewma_grade": 1.27, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-36", "blast_id": "TR-3140-36", "timestamp": datetime(2026, 8, 15), "bench": 3140, "tonnage": 51687, "plant_feed_grade": 1.1, "predicted_base_krig": 0.9, "predicted_bayesian": 1.02, "residual_base": 0.19, "residual_bayesian": 0.07, "cusum_high": 0.16, "cusum_low": 0.0, "ewma_grade": 1.2, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-37", "blast_id": "TR-3140-37", "timestamp": datetime(2026, 8, 18), "bench": 3140, "tonnage": 48177, "plant_feed_grade": 1.33, "predicted_base_krig": 1.16, "predicted_bayesian": 1.27, "residual_base": 0.16, "residual_bayesian": 0.05, "cusum_high": 0.25, "cusum_low": 0.0, "ewma_grade": 1.2, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-38", "blast_id": "TR-3140-38", "timestamp": datetime(2026, 8, 21), "bench": 3140, "tonnage": 50060, "plant_feed_grade": 1.24, "predicted_base_krig": 1.04, "predicted_bayesian": 1.18, "residual_base": 0.2, "residual_bayesian": 0.06, "cusum_high": 0.29, "cusum_low": 0.0, "ewma_grade": 1.26, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-39", "blast_id": "TR-3140-39", "timestamp": datetime(2026, 8, 25), "bench": 3140, "tonnage": 49909, "plant_feed_grade": 1.07, "predicted_base_krig": 0.9, "predicted_bayesian": 1.04, "residual_base": 0.17, "residual_bayesian": 0.04, "cusum_high": 0.02, "cusum_low": 0.0, "ewma_grade": 1.27, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-40", "blast_id": "TR-3140-40", "timestamp": datetime(2026, 8, 29), "bench": 3140, "tonnage": 49611, "plant_feed_grade": 1.06, "predicted_base_krig": 0.84, "predicted_bayesian": 1.03, "residual_base": 0.23, "residual_bayesian": 0.03, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 1.2, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-41", "blast_id": "TR-3140-41", "timestamp": datetime(2026, 9, 1), "bench": 3140, "tonnage": 51282, "plant_feed_grade": 1.43, "predicted_base_krig": 1.29, "predicted_bayesian": 1.4, "residual_base": 0.15, "residual_bayesian": 0.04, "cusum_high": 0.2, "cusum_low": 0.0, "ewma_grade": 1.23, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-42", "blast_id": "TR-3140-42", "timestamp": datetime(2026, 9, 3), "bench": 3140, "tonnage": 50750, "plant_feed_grade": 1.24, "predicted_base_krig": 1.01, "predicted_bayesian": 1.18, "residual_base": 0.23, "residual_bayesian": 0.05, "cusum_high": 0.28, "cusum_low": 0.0, "ewma_grade": 1.16, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-43", "blast_id": "TR-3140-43", "timestamp": datetime(2026, 9, 6), "bench": 3140, "tonnage": 49429, "plant_feed_grade": 1.16, "predicted_base_krig": 0.96, "predicted_bayesian": 1.12, "residual_base": 0.21, "residual_bayesian": 0.04, "cusum_high": 0.32, "cusum_low": 0.0, "ewma_grade": 1.24, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-44", "blast_id": "TR-3140-44", "timestamp": datetime(2026, 9, 10), "bench": 3140, "tonnage": 51642, "plant_feed_grade": 1.33, "predicted_base_krig": 1.11, "predicted_bayesian": 1.31, "residual_base": 0.22, "residual_bayesian": 0.03, "cusum_high": 0.2, "cusum_low": 0.0, "ewma_grade": 1.19, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-45", "blast_id": "TR-3140-45", "timestamp": datetime(2026, 9, 11), "bench": 3140, "tonnage": 50697, "plant_feed_grade": 1.18, "predicted_base_krig": 0.97, "predicted_bayesian": 1.11, "residual_base": 0.21, "residual_bayesian": 0.07, "cusum_high": 0.11, "cusum_low": 0.0, "ewma_grade": 1.25, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-46", "blast_id": "TR-3140-46", "timestamp": datetime(2026, 9, 14), "bench": 3140, "tonnage": 50529, "plant_feed_grade": 1.26, "predicted_base_krig": 1.04, "predicted_bayesian": 1.2, "residual_base": 0.22, "residual_bayesian": 0.06, "cusum_high": 0.23, "cusum_low": 0.0, "ewma_grade": 1.23, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-47", "blast_id": "TR-3140-47", "timestamp": datetime(2026, 9, 18), "bench": 3140, "tonnage": 48757, "plant_feed_grade": 1.33, "predicted_base_krig": 1.15, "predicted_bayesian": 1.26, "residual_base": 0.17, "residual_bayesian": 0.07, "cusum_high": 0.4, "cusum_low": 0.0, "ewma_grade": 1.21, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-48", "blast_id": "TR-3140-48", "timestamp": datetime(2026, 9, 20), "bench": 3140, "tonnage": 48046, "plant_feed_grade": 1.41, "predicted_base_krig": 1.23, "predicted_bayesian": 1.35, "residual_base": 0.18, "residual_bayesian": 0.05, "cusum_high": 0.4, "cusum_low": 0.0, "ewma_grade": 1.14, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-49", "blast_id": "TR-3140-49", "timestamp": datetime(2026, 9, 23), "bench": 3140, "tonnage": 51287, "plant_feed_grade": 1.14, "predicted_base_krig": 0.96, "predicted_bayesian": 1.1, "residual_base": 0.18, "residual_bayesian": 0.05, "cusum_high": 0.21, "cusum_low": 0.0, "ewma_grade": 1.19, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3140-50", "blast_id": "TR-3140-50", "timestamp": datetime(2026, 9, 27), "bench": 3140, "tonnage": 51918, "plant_feed_grade": 1.32, "predicted_base_krig": 1.16, "predicted_bayesian": 1.25, "residual_base": 0.16, "residual_bayesian": 0.06, "cusum_high": 0.39, "cusum_low": 0.0, "ewma_grade": 1.14, "ucl": 1.35, "lcl": 0.8, "target_grade": 1.05},
        {"point_id": "BL-3125-01", "blast_id": "TR-3125-01", "timestamp": datetime(2026, 4, 5), "bench": 3125, "tonnage": 48781, "plant_feed_grade": 1.04, "predicted_base_krig": 0.88, "predicted_bayesian": 1.02, "residual_base": 0.16, "residual_bayesian": 0.02, "cusum_high": 0.16, "cusum_low": 0.0, "ewma_grade": 1.06, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-02", "blast_id": "TR-3125-02", "timestamp": datetime(2026, 4, 6), "bench": 3125, "tonnage": 47965, "plant_feed_grade": 0.89, "predicted_base_krig": 0.65, "predicted_bayesian": 0.86, "residual_base": 0.23, "residual_bayesian": 0.03, "cusum_high": 0.19, "cusum_low": 0.0, "ewma_grade": 1.02, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-03", "blast_id": "TR-3125-03", "timestamp": datetime(2026, 4, 11), "bench": 3125, "tonnage": 47550, "plant_feed_grade": 0.94, "predicted_base_krig": 0.74, "predicted_bayesian": 0.92, "residual_base": 0.21, "residual_bayesian": 0.02, "cusum_high": 0.04, "cusum_low": 0.0, "ewma_grade": 0.99, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-04", "blast_id": "TR-3125-04", "timestamp": datetime(2026, 4, 13), "bench": 3125, "tonnage": 48382, "plant_feed_grade": 1.22, "predicted_base_krig": 1.11, "predicted_bayesian": 1.22, "residual_base": 0.11, "residual_bayesian": -0.0, "cusum_high": 0.34, "cusum_low": 0.0, "ewma_grade": 1.06, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-05", "blast_id": "TR-3125-05", "timestamp": datetime(2026, 4, 15), "bench": 3125, "tonnage": 49909, "plant_feed_grade": 0.86, "predicted_base_krig": 0.7, "predicted_bayesian": 0.84, "residual_base": 0.16, "residual_bayesian": 0.02, "cusum_high": 0.22, "cusum_low": 0.0, "ewma_grade": 1.04, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-06", "blast_id": "TR-3125-06", "timestamp": datetime(2026, 4, 19), "bench": 3125, "tonnage": 47170, "plant_feed_grade": 0.61, "predicted_base_krig": 0.47, "predicted_bayesian": 0.56, "residual_base": 0.15, "residual_bayesian": 0.05, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.96, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-07", "blast_id": "TR-3125-07", "timestamp": datetime(2026, 4, 23), "bench": 3125, "tonnage": 48187, "plant_feed_grade": 1.11, "predicted_base_krig": 0.96, "predicted_bayesian": 1.05, "residual_base": 0.14, "residual_bayesian": 0.06, "cusum_high": 0.14, "cusum_low": 0.0, "ewma_grade": 0.97, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-08", "blast_id": "TR-3125-08", "timestamp": datetime(2026, 4, 24), "bench": 3125, "tonnage": 47938, "plant_feed_grade": 1.16, "predicted_base_krig": 0.98, "predicted_bayesian": 1.14, "residual_base": 0.18, "residual_bayesian": 0.02, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 0.9, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-09", "blast_id": "TR-3125-09", "timestamp": datetime(2026, 4, 29), "bench": 3125, "tonnage": 49648, "plant_feed_grade": 1.1, "predicted_base_krig": 0.98, "predicted_bayesian": 1.09, "residual_base": 0.12, "residual_bayesian": 0.01, "cusum_high": 0.38, "cusum_low": 0.0, "ewma_grade": 1.04, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-10", "blast_id": "TR-3125-10", "timestamp": datetime(2026, 4, 30), "bench": 3125, "tonnage": 47290, "plant_feed_grade": 0.93, "predicted_base_krig": 0.72, "predicted_bayesian": 0.91, "residual_base": 0.22, "residual_bayesian": 0.03, "cusum_high": 0.23, "cusum_low": 0.0, "ewma_grade": 0.97, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-11", "blast_id": "TR-3125-11", "timestamp": datetime(2026, 5, 3), "bench": 3125, "tonnage": 49613, "plant_feed_grade": 0.93, "predicted_base_krig": 0.77, "predicted_bayesian": 0.89, "residual_base": 0.17, "residual_bayesian": 0.05, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 0.95, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-12", "blast_id": "TR-3125-12", "timestamp": datetime(2026, 5, 7), "bench": 3125, "tonnage": 46247, "plant_feed_grade": 0.86, "predicted_base_krig": 0.67, "predicted_bayesian": 0.83, "residual_base": 0.2, "residual_bayesian": 0.03, "cusum_high": 0.11, "cusum_low": 0.0, "ewma_grade": 0.99, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-13", "blast_id": "TR-3125-13", "timestamp": datetime(2026, 5, 10), "bench": 3125, "tonnage": 45232, "plant_feed_grade": 0.93, "predicted_base_krig": 0.78, "predicted_bayesian": 0.9, "residual_base": 0.15, "residual_bayesian": 0.04, "cusum_high": 0.29, "cusum_low": 0.0, "ewma_grade": 0.99, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-14", "blast_id": "TR-3125-14", "timestamp": datetime(2026, 5, 13), "bench": 3125, "tonnage": 49499, "plant_feed_grade": 1.01, "predicted_base_krig": 0.81, "predicted_bayesian": 0.94, "residual_base": 0.2, "residual_bayesian": 0.08, "cusum_high": 0.28, "cusum_low": 0.0, "ewma_grade": 0.95, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-15", "blast_id": "TR-3125-15", "timestamp": datetime(2026, 5, 16), "bench": 3125, "tonnage": 49139, "plant_feed_grade": 0.85, "predicted_base_krig": 0.69, "predicted_bayesian": 0.81, "residual_base": 0.17, "residual_bayesian": 0.05, "cusum_high": 0.19, "cusum_low": 0.0, "ewma_grade": 1.05, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-16", "blast_id": "TR-3125-16", "timestamp": datetime(2026, 5, 18), "bench": 3125, "tonnage": 49860, "plant_feed_grade": 0.84, "predicted_base_krig": 0.69, "predicted_bayesian": 0.78, "residual_base": 0.15, "residual_bayesian": 0.07, "cusum_high": 0.03, "cusum_low": 0.0, "ewma_grade": 1.12, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-17", "blast_id": "TR-3125-17", "timestamp": datetime(2026, 5, 21), "bench": 3125, "tonnage": 49902, "plant_feed_grade": 0.88, "predicted_base_krig": 0.71, "predicted_bayesian": 0.85, "residual_base": 0.17, "residual_bayesian": 0.03, "cusum_high": 0.25, "cusum_low": 0.0, "ewma_grade": 1.1, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-18", "blast_id": "TR-3125-18", "timestamp": datetime(2026, 5, 25), "bench": 3125, "tonnage": 45408, "plant_feed_grade": 0.96, "predicted_base_krig": 0.79, "predicted_bayesian": 0.93, "residual_base": 0.17, "residual_bayesian": 0.03, "cusum_high": 0.28, "cusum_low": 0.0, "ewma_grade": 1.09, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-19", "blast_id": "TR-3125-19", "timestamp": datetime(2026, 5, 29), "bench": 3125, "tonnage": 45487, "plant_feed_grade": 0.85, "predicted_base_krig": 0.67, "predicted_bayesian": 0.78, "residual_base": 0.18, "residual_bayesian": 0.06, "cusum_high": 0.17, "cusum_low": 0.0, "ewma_grade": 1.03, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-20", "blast_id": "TR-3125-20", "timestamp": datetime(2026, 6, 1), "bench": 3125, "tonnage": 47296, "plant_feed_grade": 0.9, "predicted_base_krig": 0.73, "predicted_bayesian": 0.89, "residual_base": 0.17, "residual_bayesian": 0.01, "cusum_high": 0.24, "cusum_low": 0.0, "ewma_grade": 1.0, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-21", "blast_id": "TR-3125-21", "timestamp": datetime(2026, 6, 3), "bench": 3125, "tonnage": 48783, "plant_feed_grade": 0.91, "predicted_base_krig": 0.72, "predicted_bayesian": 0.86, "residual_base": 0.19, "residual_bayesian": 0.05, "cusum_high": 0.01, "cusum_low": 0.0, "ewma_grade": 0.95, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-22", "blast_id": "TR-3125-22", "timestamp": datetime(2026, 6, 6), "bench": 3125, "tonnage": 49733, "plant_feed_grade": 1.05, "predicted_base_krig": 0.85, "predicted_bayesian": 1.0, "residual_base": 0.2, "residual_bayesian": 0.05, "cusum_high": 0.3, "cusum_low": 0.0, "ewma_grade": 0.97, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-23", "blast_id": "TR-3125-23", "timestamp": datetime(2026, 6, 9), "bench": 3125, "tonnage": 46412, "plant_feed_grade": 1.26, "predicted_base_krig": 1.15, "predicted_bayesian": 1.21, "residual_base": 0.11, "residual_bayesian": 0.05, "cusum_high": 0.33, "cusum_low": 0.0, "ewma_grade": 0.97, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-24", "blast_id": "TR-3125-24", "timestamp": datetime(2026, 6, 13), "bench": 3125, "tonnage": 48878, "plant_feed_grade": 1.04, "predicted_base_krig": 0.85, "predicted_bayesian": 0.99, "residual_base": 0.19, "residual_bayesian": 0.05, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 1.06, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-25", "blast_id": "TR-3125-25", "timestamp": datetime(2026, 6, 16), "bench": 3125, "tonnage": 48213, "plant_feed_grade": 1.18, "predicted_base_krig": 0.99, "predicted_bayesian": 1.12, "residual_base": 0.19, "residual_bayesian": 0.06, "cusum_high": 0.41, "cusum_low": 0.0, "ewma_grade": 0.94, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-26", "blast_id": "TR-3125-26", "timestamp": datetime(2026, 6, 19), "bench": 3125, "tonnage": 46583, "plant_feed_grade": 0.83, "predicted_base_krig": 0.66, "predicted_bayesian": 0.81, "residual_base": 0.17, "residual_bayesian": 0.02, "cusum_high": 0.07, "cusum_low": 0.0, "ewma_grade": 1.03, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-27", "blast_id": "TR-3125-27", "timestamp": datetime(2026, 6, 22), "bench": 3125, "tonnage": 48663, "plant_feed_grade": 1.36, "predicted_base_krig": 1.19, "predicted_bayesian": 1.31, "residual_base": 0.16, "residual_bayesian": 0.04, "cusum_high": 0.32, "cusum_low": 0.0, "ewma_grade": 0.98, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-28", "blast_id": "TR-3125-28", "timestamp": datetime(2026, 6, 24), "bench": 3125, "tonnage": 45612, "plant_feed_grade": 0.88, "predicted_base_krig": 0.74, "predicted_bayesian": 0.84, "residual_base": 0.14, "residual_bayesian": 0.04, "cusum_high": 0.18, "cusum_low": 0.0, "ewma_grade": 1.02, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-29", "blast_id": "TR-3125-29", "timestamp": datetime(2026, 6, 26), "bench": 3125, "tonnage": 47636, "plant_feed_grade": 0.83, "predicted_base_krig": 0.66, "predicted_bayesian": 0.79, "residual_base": 0.18, "residual_bayesian": 0.04, "cusum_high": 0.21, "cusum_low": 0.0, "ewma_grade": 0.99, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-30", "blast_id": "TR-3125-30", "timestamp": datetime(2026, 6, 29), "bench": 3125, "tonnage": 45553, "plant_feed_grade": 0.93, "predicted_base_krig": 0.72, "predicted_bayesian": 0.9, "residual_base": 0.21, "residual_bayesian": 0.03, "cusum_high": 0.15, "cusum_low": 0.0, "ewma_grade": 0.99, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-31", "blast_id": "TR-3125-31", "timestamp": datetime(2026, 7, 3), "bench": 3125, "tonnage": 49141, "plant_feed_grade": 0.98, "predicted_base_krig": 0.85, "predicted_bayesian": 0.94, "residual_base": 0.13, "residual_bayesian": 0.04, "cusum_high": 0.09, "cusum_low": 0.0, "ewma_grade": 0.89, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-32", "blast_id": "TR-3125-32", "timestamp": datetime(2026, 7, 5), "bench": 3125, "tonnage": 45709, "plant_feed_grade": 1.12, "predicted_base_krig": 0.96, "predicted_bayesian": 1.07, "residual_base": 0.15, "residual_bayesian": 0.04, "cusum_high": 0.33, "cusum_low": 0.0, "ewma_grade": 0.98, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-33", "blast_id": "TR-3125-33", "timestamp": datetime(2026, 7, 10), "bench": 3125, "tonnage": 48690, "plant_feed_grade": 1.06, "predicted_base_krig": 0.86, "predicted_bayesian": 1.06, "residual_base": 0.21, "residual_bayesian": 0.0, "cusum_high": 0.33, "cusum_low": 0.0, "ewma_grade": 0.92, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-34", "blast_id": "TR-3125-34", "timestamp": datetime(2026, 7, 11), "bench": 3125, "tonnage": 48276, "plant_feed_grade": 0.93, "predicted_base_krig": 0.77, "predicted_bayesian": 0.87, "residual_base": 0.16, "residual_bayesian": 0.06, "cusum_high": 0.27, "cusum_low": 0.0, "ewma_grade": 1.03, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-35", "blast_id": "TR-3125-35", "timestamp": datetime(2026, 7, 16), "bench": 3125, "tonnage": 46526, "plant_feed_grade": 1.12, "predicted_base_krig": 0.91, "predicted_bayesian": 1.08, "residual_base": 0.21, "residual_bayesian": 0.04, "cusum_high": 0.13, "cusum_low": 0.0, "ewma_grade": 1.1, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-36", "blast_id": "TR-3125-36", "timestamp": datetime(2026, 7, 17), "bench": 3125, "tonnage": 46163, "plant_feed_grade": 0.93, "predicted_base_krig": 0.8, "predicted_bayesian": 0.9, "residual_base": 0.13, "residual_bayesian": 0.03, "cusum_high": 0.25, "cusum_low": 0.0, "ewma_grade": 1.01, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-37", "blast_id": "TR-3125-37", "timestamp": datetime(2026, 7, 22), "bench": 3125, "tonnage": 47802, "plant_feed_grade": 0.83, "predicted_base_krig": 0.69, "predicted_bayesian": 0.8, "residual_base": 0.14, "residual_bayesian": 0.03, "cusum_high": 0.08, "cusum_low": 0.0, "ewma_grade": 1.03, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-38", "blast_id": "TR-3125-38", "timestamp": datetime(2026, 7, 25), "bench": 3125, "tonnage": 47063, "plant_feed_grade": 0.82, "predicted_base_krig": 0.63, "predicted_bayesian": 0.76, "residual_base": 0.19, "residual_bayesian": 0.06, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 0.98, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-39", "blast_id": "TR-3125-39", "timestamp": datetime(2026, 7, 26), "bench": 3125, "tonnage": 46400, "plant_feed_grade": 0.93, "predicted_base_krig": 0.75, "predicted_bayesian": 0.89, "residual_base": 0.17, "residual_bayesian": 0.03, "cusum_high": 0.1, "cusum_low": 0.0, "ewma_grade": 1.01, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-40", "blast_id": "TR-3125-40", "timestamp": datetime(2026, 7, 31), "bench": 3125, "tonnage": 46407, "plant_feed_grade": 1.03, "predicted_base_krig": 0.87, "predicted_bayesian": 1.01, "residual_base": 0.16, "residual_bayesian": 0.02, "cusum_high": 0.2, "cusum_low": 0.0, "ewma_grade": 0.97, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-41", "blast_id": "TR-3125-41", "timestamp": datetime(2026, 8, 1), "bench": 3125, "tonnage": 45230, "plant_feed_grade": 0.95, "predicted_base_krig": 0.77, "predicted_bayesian": 0.9, "residual_base": 0.18, "residual_bayesian": 0.04, "cusum_high": 0.16, "cusum_low": 0.0, "ewma_grade": 0.99, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-42", "blast_id": "TR-3125-42", "timestamp": datetime(2026, 8, 6), "bench": 3125, "tonnage": 48715, "plant_feed_grade": 1.11, "predicted_base_krig": 0.89, "predicted_bayesian": 1.05, "residual_base": 0.22, "residual_bayesian": 0.06, "cusum_high": 0.38, "cusum_low": 0.0, "ewma_grade": 0.95, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-43", "blast_id": "TR-3125-43", "timestamp": datetime(2026, 8, 9), "bench": 3125, "tonnage": 45926, "plant_feed_grade": 1.06, "predicted_base_krig": 0.92, "predicted_bayesian": 1.04, "residual_base": 0.14, "residual_bayesian": 0.02, "cusum_high": 0.24, "cusum_low": 0.0, "ewma_grade": 1.01, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-44", "blast_id": "TR-3125-44", "timestamp": datetime(2026, 8, 10), "bench": 3125, "tonnage": 48945, "plant_feed_grade": 0.93, "predicted_base_krig": 0.78, "predicted_bayesian": 0.86, "residual_base": 0.15, "residual_bayesian": 0.07, "cusum_high": 0.17, "cusum_low": 0.0, "ewma_grade": 0.98, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-45", "blast_id": "TR-3125-45", "timestamp": datetime(2026, 8, 13), "bench": 3125, "tonnage": 49394, "plant_feed_grade": 0.87, "predicted_base_krig": 0.71, "predicted_bayesian": 0.85, "residual_base": 0.16, "residual_bayesian": 0.02, "cusum_high": 0, "cusum_low": 0.0, "ewma_grade": 1.03, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-46", "blast_id": "TR-3125-46", "timestamp": datetime(2026, 8, 18), "bench": 3125, "tonnage": 45687, "plant_feed_grade": 0.93, "predicted_base_krig": 0.76, "predicted_bayesian": 0.89, "residual_base": 0.16, "residual_bayesian": 0.04, "cusum_high": 0.28, "cusum_low": 0.0, "ewma_grade": 1.04, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-47", "blast_id": "TR-3125-47", "timestamp": datetime(2026, 8, 21), "bench": 3125, "tonnage": 48513, "plant_feed_grade": 1.29, "predicted_base_krig": 1.09, "predicted_bayesian": 1.28, "residual_base": 0.2, "residual_bayesian": 0.02, "cusum_high": 0.35, "cusum_low": 0.0, "ewma_grade": 1.09, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-48", "blast_id": "TR-3125-48", "timestamp": datetime(2026, 8, 23), "bench": 3125, "tonnage": 49752, "plant_feed_grade": 0.97, "predicted_base_krig": 0.77, "predicted_bayesian": 0.97, "residual_base": 0.2, "residual_bayesian": -0.0, "cusum_high": 0.17, "cusum_low": 0.0, "ewma_grade": 0.99, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-49", "blast_id": "TR-3125-49", "timestamp": datetime(2026, 8, 26), "bench": 3125, "tonnage": 46194, "plant_feed_grade": 1.13, "predicted_base_krig": 0.95, "predicted_bayesian": 1.1, "residual_base": 0.18, "residual_bayesian": 0.02, "cusum_high": 0.4, "cusum_low": 0.0, "ewma_grade": 1.01, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
        {"point_id": "BL-3125-50", "blast_id": "TR-3125-50", "timestamp": datetime(2026, 8, 28), "bench": 3125, "tonnage": 46403, "plant_feed_grade": 0.97, "predicted_base_krig": 0.74, "predicted_bayesian": 0.94, "residual_base": 0.23, "residual_bayesian": 0.03, "cusum_high": 0.19, "cusum_low": 0.0, "ewma_grade": 0.94, "ucl": 1.15, "lcl": 0.65, "target_grade": 0.9},
    ]
    for pcp in pcp_data:
        db.add(ProcessControlPoint(project_id=esperanza_id, **pcp))

    # 8. Training Loss History
    training_data = [
        {"epoch": 10, "elbo_loss": 4.82, "kl_divergence": 1.95, "reconstruction_loss": 2.87, "val_rmse": 0.38, "ece_score": 0.142},
        {"epoch": 20, "elbo_loss": 3.45, "kl_divergence": 1.48, "reconstruction_loss": 1.97, "val_rmse": 0.29, "ece_score": 0.098},
        {"epoch": 30, "elbo_loss": 2.61, "kl_divergence": 1.15, "reconstruction_loss": 1.46, "val_rmse": 0.22, "ece_score": 0.071},
        {"epoch": 40, "elbo_loss": 1.98, "kl_divergence": 0.89, "reconstruction_loss": 1.09, "val_rmse": 0.17, "ece_score": 0.052},
        {"epoch": 50, "elbo_loss": 1.54, "kl_divergence": 0.72, "reconstruction_loss": 0.82, "val_rmse": 0.13, "ece_score": 0.041},
        {"epoch": 60, "elbo_loss": 1.22, "kl_divergence": 0.61, "reconstruction_loss": 0.61, "val_rmse": 0.10, "ece_score": 0.034},
        {"epoch": 70, "elbo_loss": 1.05, "kl_divergence": 0.54, "reconstruction_loss": 0.51, "val_rmse": 0.08, "ece_score": 0.028},
        {"epoch": 80, "elbo_loss": 0.94, "kl_divergence": 0.49, "reconstruction_loss": 0.45, "val_rmse": 0.07, "ece_score": 0.024},
        {"epoch": 90, "elbo_loss": 0.87, "kl_divergence": 0.46, "reconstruction_loss": 0.41, "val_rmse": 0.06, "ece_score": 0.021},
        {"epoch": 100, "elbo_loss": 0.82, "kl_divergence": 0.44, "reconstruction_loss": 0.38, "val_rmse": 0.05, "ece_score": 0.018},
    ]

    for t in training_data:
        db.add(TrainingLossHistory(project_id=esperanza_id, **t))

    await db.commit()
