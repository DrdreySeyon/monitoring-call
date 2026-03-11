import logging
import traceback
from datetime import datetime
from typing import Optional
import json

from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from scheduler import start_scheduler #newwww

from config import settings, API_TITLE, API_DESCRIPTION, API_VERSION
from database import get_db, create_tables, test_database_connection
from models import (
    Call,
    Scenario,
    CallRequest,
    ScenarioCreate,
    ScenarioPatch
)
from ari import (
    perform_call,
    test_ari_connection,
    fetch_cdr_duration,
    fetch_multiple_cdr_durations
)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
)

create_tables()


# ============================================================
# EXCEPTIONS
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée sur {request.url}: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur", "type": "internal_error"}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException sur {request.url}: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": "http_error"}
    )


# ============================================================
# GENERAL
# ============================================================

@app.on_event("startup")
def startup_event():
    logger.info("Démarrage du scheduler...")
    start_scheduler()  # Démarre les tâches programmées
    logger.info("Scheduler démarré avec succès.")



@app.get(f"{settings.api_prefix}")
def api_root():
    return {
        "message": "BACKEND FASTAPI OK",
        "version": API_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "features": [
            "DTMF Support",
            "ARI Integration",
            "MySQL CDR",
            "Health Monitoring"
        ]
    }


@app.get(f"{settings.api_prefix}/health")
def health():
    return {
        "status": "ok",
        "service": "fastapi-backend",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get(f"{settings.api_prefix}/health/detailed")
def detailed_health(db: Session = Depends(get_db)):
    health_status = {
        "status": "ok",
        "service": "fastapi-backend",
        "version": API_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    db_check = test_database_connection(db)
    health_status["checks"]["database"] = db_check
    if db_check["status"] == "error":
        health_status["status"] = "degraded"

    ari_check = test_ari_connection()
    health_status["checks"]["ari"] = ari_check
    if ari_check["status"] == "error":
        health_status["status"] = "degraded"

    return health_status


# ============================================================
# CALLS
# ============================================================

@app.post(f"{settings.api_prefix}/calls")
async def initiate_call(req: CallRequest, db: Session = Depends(get_db)):
    call_row, ari_response = perform_call(
        db=db,
        caller=req.caller,
        callee=req.callee,
        trunk=req.trunk,
        call_time_s=req.call_time_s,
        dtmf=req.dtmf,
        time_s_before_dtmf=req.time_s_before_dtmf,
        time_ms_between_dtmf=req.time_ms_between_dtmf
    )

    return {
        "db_call": {
            "id": call_row.id,
            "endpoint": call_row.endpoint,
            "caller": call_row.caller,
            "callee": call_row.callee,
            "trunk": call_row.trunk,
            "channel_id": call_row.channel_id,
            "call_time_s": call_row.call_time_s,
            "duration": call_row.duration,
            "dtmf": call_row.dtmf,
            "time_s_before_dtmf": call_row.time_s_before_dtmf,
            "time_ms_between_dtmf": call_row.time_ms_between_dtmf,
            "status": call_row.status,
            "error_message": call_row.error_message,
            "created_at": str(call_row.created_at)
        },
        "ari_response": ari_response
    }


@app.get(f"{settings.api_prefix}/calls/stats")
def get_calls_stats(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Call)

        if from_date:
            from_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
            query = query.filter(Call.created_at >= from_dt)

        if to_date:
            to_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
            query = query.filter(Call.created_at <= to_dt)

        total_calls = query.count()
        successful_calls = query.filter(Call.status == "success").count()
        failed_calls = query.filter(Call.status == "failed").count()
        in_progress_calls = query.filter(Call.status == "in_progress").count()

        dtmf_calls = query.filter(Call.dtmf.isnot(None)).filter(Call.dtmf != "").count()

        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0

        avg_duration = db.query(func.avg(Call.duration)).filter(
            Call.duration.isnot(None)
        ).scalar()
        avg_duration = float(avg_duration) if avg_duration is not None else 0

        dtmf_stats = {
            "most_used_sequences": [],
            "unique_sequences": 0,
            "avg_dtmf_delay": None,
            "avg_dtmf_interval": None
        }

        if dtmf_calls > 0:
            dtmf_sequences = db.query(
                Call.dtmf,
                func.count(Call.dtmf).label("count")
            ).filter(
                Call.dtmf.isnot(None)
            ).filter(
                Call.dtmf != ""
            ).group_by(Call.dtmf).all()

            dtmf_stats["most_used_sequences"] = [
                {"sequence": seq, "count": count}
                for seq, count in dtmf_sequences[:5]
            ]
            dtmf_stats["unique_sequences"] = len(dtmf_sequences)

            avg_delay = db.query(func.avg(Call.time_s_before_dtmf)).filter(
                Call.time_s_before_dtmf.isnot(None)
            ).scalar()
            if avg_delay is not None:
                dtmf_stats["avg_dtmf_delay"] = float(avg_delay)

            avg_interval = db.query(func.avg(Call.time_ms_between_dtmf)).filter(
                Call.time_ms_between_dtmf.isnot(None)
            ).scalar()
            if avg_interval is not None:
                dtmf_stats["avg_dtmf_interval"] = float(avg_interval)

        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "in_progress_calls": in_progress_calls,
            "success_rate": round(success_rate, 2),
            "average_duration_seconds": avg_duration,
            "dtmf_calls": dtmf_calls,
            "dtmf_usage_rate": round((dtmf_calls / total_calls * 100) if total_calls > 0 else 0, 2),
            "dtmf_stats": dtmf_stats,
            "period": {
                "from": from_date,
                "to": to_date
            }
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Format de date invalide: {str(exc)}")
    except Exception as exc:
        logger.error(f"Erreur lors du calcul des statistiques: {exc}")
        raise HTTPException(status_code=500, detail="Erreur lors du calcul des statistiques")


@app.get(f"{settings.api_prefix}/calls/history")
def get_calls_history(
    caller: Optional[str] = None,
    callee: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    include_duration: bool = True,
    db: Session = Depends(get_db)
):
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="page et page_size doivent être >= 1")
    if page_size > 100:
        raise HTTPException(status_code=400, detail="page_size ne peut pas dépasser 100")

    query = db.query(Call)

    if caller:
        query = query.filter(Call.caller.ilike(f"%{caller.strip()}%"))
    if callee:
        query = query.filter(Call.callee.ilike(f"%{callee.strip()}%"))
    if category:
        query = query.filter(Call.scenario_category.ilike(f"%{category.strip()}%"))
    if status:
        query = query.filter(Call.status == status.strip())

    total = query.count()
    query = query.order_by(Call.created_at.desc())

    offset = (page - 1) * page_size
    rows = query.offset(offset).limit(page_size).all()

    if include_duration:
        calls_without_duration = [
            c for c in rows
            if c.duration is None and c.channel_id and c.status == "success"
        ]

        if calls_without_duration:
            channel_ids = [c.channel_id for c in calls_without_duration]
            cdr_map = fetch_multiple_cdr_durations(channel_ids, db)

            updated_calls = []
            for call in calls_without_duration:
                if call.channel_id in cdr_map:
                    call.duration = cdr_map[call.channel_id]
                    updated_calls.append(call)

            if updated_calls:
                try:
                    db.commit()
                except Exception as exc:
                    logger.error(f"Erreur lors de la mise à jour des durées: {exc}")
                    db.rollback()

    items = []
    for c in rows:
        items.append({
            "id": c.id,
            "endpoint": c.endpoint,
            "caller": c.caller,
            "callee": c.callee,
            "trunk": c.trunk,
            "channel_id": c.channel_id,
            "call_time_s": c.call_time_s,
            "duration": c.duration,
            "dtmf": c.dtmf,
            "time_s_before_dtmf": c.time_s_before_dtmf,
            "time_ms_between_dtmf": c.time_ms_between_dtmf,
            "status": c.status,
            "error_message": c.error_message,
            "scenario_id": c.scenario_id,
            "scenario_name": c.scenario_name,
            "scenario_keyword": c.scenario_keyword,
            "scenario_category": c.scenario_category,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
        "items": items
    }

@app.get(f"{settings.api_prefix}/calls/history/export")
def export_calls_history(
    caller: Optional[str] = None,
    callee: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Call)

    if caller:
        query = query.filter(Call.caller.ilike(f"%{caller.strip()}%"))
    if callee:
        query = query.filter(Call.callee.ilike(f"%{callee.strip()}%"))
    if category:
        query = query.filter(Call.scenario_category.ilike(f"%{category.strip()}%"))
    if status:
        query = query.filter(Call.status == status.strip())

    rows = query.all()

    # Préparez les données pour l'export
    data = [{"id": call.id, "caller": call.caller, "callee": call.callee, "status": call.status, "created_at": call.created_at.isoformat() if call.created_at else None} for call in rows]

    content = json.dumps(data, ensure_ascii=False, indent=2)

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="calls_history_export.json"'
        }
    )

@app.get(f"{settings.api_prefix}/calls/{{call_id}}")
def get_call_details(call_id: int, db: Session = Depends(get_db)):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Appel non trouvé")

    if call.duration is None and call.channel_id and call.status == "success":
        duration = fetch_cdr_duration(call.channel_id, db)
        if duration is not None:
            call.duration = duration
            db.commit()
            db.refresh(call)

    return {
        "id": call.id,
        "endpoint": call.endpoint,
        "caller": call.caller,
        "callee": call.callee,
        "trunk": call.trunk,
        "channel_id": call.channel_id,
        "call_time_s": call.call_time_s,
        "duration": call.duration,
        "dtmf": call.dtmf,
        "time_s_before_dtmf": call.time_s_before_dtmf,
        "time_ms_between_dtmf": call.time_ms_between_dtmf,
        "status": call.status,
        "error_message": call.error_message,
        "scenario_id": call.scenario_id,
        "scenario_name": call.scenario_name,
        "scenario_keyword": call.scenario_keyword,
        "scenario_category": call.scenario_category,
        "created_at": call.created_at.isoformat() if call.created_at else None
    }


# ============================================================
# SCENARIOS
# ============================================================

@app.get(f"{settings.api_prefix}/scenarios")
def get_scenarios(page: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Scenario).order_by(Scenario.created_at.desc())

    if page is None:
        rows = query.all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "keyword": s.keyword,
                "category": s.category,
                "caller": s.caller,
                "callee": s.callee,
                "trunk": s.trunk,
                "call_time_s": s.call_time_s,
                "dtmf": s.dtmf,
                "time_s_before_dtmf": s.time_s_before_dtmf,
                "time_ms_between_dtmf": s.time_ms_between_dtmf,
                "frequency": s.frequency,
                "active": bool(s.active),
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in rows
        ]

    rows = query.limit(100).all()
    return {
        "items": rows
    }


@app.get(f"{settings.api_prefix}/scenarios/export")
def export_scenarios(db: Session = Depends(get_db)):
    rows = db.query(Scenario).order_by(Scenario.created_at.desc()).all()

    payload = {
        "exported_at": datetime.utcnow().isoformat(),
        "count": len(rows),
        "scenarios": [
            {
                "name": s.name,
                "keyword": s.keyword,
                "category": s.category,
                "caller": s.caller,
                "callee": s.callee,
                "trunk": s.trunk,
                "call_time_s": s.call_time_s,
                "dtmf": s.dtmf,
                "time_s_before_dtmf": s.time_s_before_dtmf,
                "time_ms_between_dtmf": s.time_ms_between_dtmf,
                "frequency": s.frequency,
                "active": bool(s.active),
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in rows
        ]
    }

    content = json.dumps(payload, ensure_ascii=False, indent=2)

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="scenarios_export.json"'
        }
    )


@app.post(f"{settings.api_prefix}/scenarios/import")
async def import_scenarios(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        raw = await file.read()
        data = json.loads(raw.decode("utf-8"))

        scenarios_data = data.get("scenarios") if isinstance(data, dict) else data

        if not isinstance(scenarios_data, list):
            raise HTTPException(status_code=400, detail="Format JSON invalide")

        created = 0
        skipped = 0
        errors = []

        for idx, item in enumerate(scenarios_data, start=1):
            try:
                if not isinstance(item, dict):
                    errors.append(f"Ligne {idx}: objet invalide")
                    continue

                name = item.get("name")
                keyword = item.get("keyword")
                category = item.get("category")
                caller = item.get("caller")
                callee = item.get("callee")
                trunk = item.get("trunk")

                if not name or not keyword or not category or not caller or not callee or not trunk:
                    errors.append(f"Ligne {idx}: champs obligatoires manquants")
                    continue

                existing = db.query(Scenario).filter(
                    Scenario.name == name,
                    Scenario.caller == caller,
                    Scenario.callee == callee,
                    Scenario.trunk == trunk
                ).first()

                if existing:
                    skipped += 1
                    continue

                db_scenario = Scenario(
                    name=name,
                    keyword=keyword,
                    category=category,
                    caller=caller,
                    callee=callee,
                    trunk=trunk,
                    call_time_s=item.get("call_time_s", 30),
                    dtmf=item.get("dtmf"),
                    time_s_before_dtmf=item.get("time_s_before_dtmf"),
                    time_ms_between_dtmf=item.get("time_ms_between_dtmf", 3000),
                    frequency=item.get("frequency"),
                    active=1 if item.get("active", True) else 0
                )

                db.add(db_scenario)
                created += 1

            except Exception as exc:
                errors.append(f"Ligne {idx}: {str(exc)}")

        db.commit()

        return {
            "message": "Import terminé",
            "created": created,
            "skipped": skipped,
            "errors": errors
        }

    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Fichier JSON invalide")
    except Exception as exc:
        db.rollback()
        logger.error(f"Erreur import scénarios: {exc}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'import")


@app.post(f"{settings.api_prefix}/scenarios")
async def create_scenario(scenario: ScenarioCreate, db: Session = Depends(get_db)):
    try:
        if scenario.dtmf and scenario.time_s_before_dtmf is not None:
            if scenario.time_s_before_dtmf >= scenario.call_time_s:
                raise HTTPException(
                    status_code=400,
                    detail="Le délai DTMF doit être inférieur à la durée totale de l'appel"
                )

        db_scenario = Scenario(
            name=scenario.name,
            keyword=scenario.keyword,
            category=scenario.category,
            caller=scenario.caller,
            callee=scenario.callee,
            trunk=scenario.trunk,
            call_time_s=scenario.call_time_s,
            dtmf=scenario.dtmf,
            time_s_before_dtmf=scenario.time_s_before_dtmf,
            time_ms_between_dtmf=scenario.time_ms_between_dtmf,
            frequency=scenario.frequency,
            active=1 if scenario.active else 0
        )

        db.add(db_scenario)
        db.commit()
        db.refresh(db_scenario)

        return {
            "id": db_scenario.id,
            "name": db_scenario.name,
            "keyword": db_scenario.keyword,
            "category": db_scenario.category,
            "caller": db_scenario.caller,
            "callee": db_scenario.callee,
            "trunk": db_scenario.trunk,
            "call_time_s": db_scenario.call_time_s,
            "dtmf": db_scenario.dtmf,
            "time_s_before_dtmf": db_scenario.time_s_before_dtmf,
            "time_ms_between_dtmf": db_scenario.time_ms_between_dtmf,
            "frequency": db_scenario.frequency,
            "active": bool(db_scenario.active),
            "created_at": db_scenario.created_at.isoformat() if db_scenario.created_at else None
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Erreur lors de la création du scénario: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la création du scénario")


@app.get(f"{settings.api_prefix}/scenarios/{{scenario_id}}")
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")

    return {
        "id": scenario.id,
        "name": scenario.name,
        "keyword": scenario.keyword,
        "category": scenario.category,
        "caller": scenario.caller,
        "callee": scenario.callee,
        "trunk": scenario.trunk,
        "call_time_s": scenario.call_time_s,
        "dtmf": scenario.dtmf,
        "time_s_before_dtmf": scenario.time_s_before_dtmf,
        "time_ms_between_dtmf": scenario.time_ms_between_dtmf,
        "frequency": scenario.frequency,
        "active": bool(scenario.active),
        "created_at": scenario.created_at.isoformat() if scenario.created_at else None
    }


@app.patch(f"{settings.api_prefix}/scenarios/{{scenario_id}}")
async def update_scenario(
    scenario_id: int,
    scenario_update: ScenarioPatch,
    db: Session = Depends(get_db)
):
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")

    try:
        update_data = scenario_update.dict(exclude_unset=True)

        call_time = update_data.get("call_time_s", db_scenario.call_time_s)
        dtmf_delay = update_data.get("time_s_before_dtmf", db_scenario.time_s_before_dtmf)
        dtmf_value = update_data.get("dtmf", db_scenario.dtmf)

        if dtmf_value and dtmf_delay is not None and dtmf_delay >= call_time:
            raise HTTPException(
                status_code=400,
                detail="Le délai DTMF doit être inférieur à la durée totale de l'appel"
            )

        for field, value in update_data.items():
            if field == "active":
                setattr(db_scenario, field, 1 if value else 0)
            else:
                setattr(db_scenario, field, value)

        db.commit()
        db.refresh(db_scenario)

        return {
            "id": db_scenario.id,
            "name": db_scenario.name,
            "keyword": db_scenario.keyword,
            "category": db_scenario.category,
            "caller": db_scenario.caller,
            "callee": db_scenario.callee,
            "trunk": db_scenario.trunk,
            "call_time_s": db_scenario.call_time_s,
            "dtmf": db_scenario.dtmf,
            "time_s_before_dtmf": db_scenario.time_s_before_dtmf,
            "time_ms_between_dtmf": db_scenario.time_ms_between_dtmf,
            "frequency": db_scenario.frequency,
            "active": bool(db_scenario.active),
            "created_at": db_scenario.created_at.isoformat() if db_scenario.created_at else None
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Erreur lors de la mise à jour du scénario {scenario_id}: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du scénario")


@app.delete(f"{settings.api_prefix}/scenarios/{{scenario_id}}")
async def delete_scenario(scenario_id: int, db: Session = Depends(get_db)):
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")

    try:
        scenario_name = db_scenario.name
        db.delete(db_scenario)
        db.commit()
        return {"message": f"Scénario '{scenario_name}' supprimé avec succès"}
    except Exception as exc:
        logger.error(f"Erreur lors de la suppression du scénario {scenario_id}: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression du scénario")


@app.post(f"{settings.api_prefix}/scenarios/{{scenario_id}}/toggle")
async def toggle_scenario(scenario_id: int, db: Session = Depends(get_db)):
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")

    try:
        new_status = 0 if db_scenario.active else 1
        db_scenario.active = new_status
        db.commit()
        db.refresh(db_scenario)

        status_text = "activé" if new_status else "désactivé"

        return {
            "id": db_scenario.id,
            "name": db_scenario.name,
            "active": bool(db_scenario.active),
            "message": f"Scénario '{db_scenario.name}' {status_text}"
        }

    except Exception as exc:
        logger.error(f"Erreur lors du changement de statut du scénario {scenario_id}: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors du changement de statut")


@app.post(f"{settings.api_prefix}/scenarios/{{scenario_id}}/call")
async def call_from_scenario(scenario_id: int, db: Session = Depends(get_db)):
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")

    if not db_scenario.active:
        raise HTTPException(status_code=400, detail="Le scénario est inactif")

    try:
        call_row, ari_response = perform_call(
            db=db,
            caller=db_scenario.caller,
            callee=db_scenario.callee,
            trunk=db_scenario.trunk,
            call_time_s=db_scenario.call_time_s,
            dtmf=db_scenario.dtmf,
            time_s_before_dtmf=db_scenario.time_s_before_dtmf,
            time_ms_between_dtmf=db_scenario.time_ms_between_dtmf
        )

        # enrichissement historique
        call_row.scenario_id = db_scenario.id
        call_row.scenario_name = db_scenario.name
        call_row.scenario_keyword = db_scenario.keyword
        call_row.scenario_category = db_scenario.category

        db.commit()
        db.refresh(call_row)

        return {
            "scenario": {
                "id": db_scenario.id,
                "name": db_scenario.name,
                "keyword": db_scenario.keyword,
                "category": db_scenario.category
            },
            "call": {
                "id": call_row.id,
                "channel_id": call_row.channel_id,
                "status": call_row.status,
                "caller": call_row.caller,
                "callee": call_row.callee,
                "trunk": call_row.trunk,
                "call_time_s": call_row.call_time_s,
                "duration": call_row.duration,
                "dtmf": call_row.dtmf,
                "time_s_before_dtmf": call_row.time_s_before_dtmf,
                "time_ms_between_dtmf": call_row.time_ms_between_dtmf,
                "scenario_id": call_row.scenario_id,
                "scenario_name": call_row.scenario_name,
                "scenario_keyword": call_row.scenario_keyword,
                "scenario_category": call_row.scenario_category,
                "created_at": call_row.created_at.isoformat() if call_row.created_at else None
            },
            "ari_response": ari_response,
            "message": f"Appel lancé depuis le scénario '{db_scenario.name}'"
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"Erreur lors du lancement d'appel depuis le scénario {scenario_id}: {exc}\n{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du lancement de l'appel: {str(exc)}"
        )


# ============================================================
# SYSTEM
# ============================================================

@app.get(f"{settings.api_prefix}/system/info")
def get_system_info():
    return {
        "service": "fastapi-backend",
        "version": API_VERSION,
        "title": API_TITLE,
        "description": API_DESCRIPTION,
        "features": [
            "DTMF Support",
            "ARI Integration",
            "MySQL CDR Integration",
            "Health Monitoring",
            "Advanced Statistics",
            "Scenario Management"
        ],
        "endpoints": {
            "health": f"{settings.api_prefix}/health",
            "calls": f"{settings.api_prefix}/calls",
            "scenarios": f"{settings.api_prefix}/scenarios",
            "stats": f"{settings.api_prefix}/calls/stats",
            "docs": f"{settings.api_prefix}/docs"
        },
        "dtmf_capabilities": {
            "supported_characters": "0-9, *, #",
            "configurable_delay": True,
            "configurable_interval": True,
            "sequence_validation": True,
            "statistics_tracking": True
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get(f"{settings.api_prefix}/system/metrics")
def get_system_metrics(db: Session = Depends(get_db)):
    try:
        total_calls = db.query(Call).count()
        total_scenarios = db.query(Scenario).count()
        active_scenarios = db.query(Scenario).filter(Scenario.active == 1).count()
        recent_calls = db.query(Call).filter(
            Call.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()

        dtmf_enabled_scenarios = db.query(Scenario).filter(
            Scenario.dtmf.isnot(None)
        ).filter(
            Scenario.dtmf != ""
        ).count()

        return {
            "total_calls": total_calls,
            "total_scenarios": total_scenarios,
            "active_scenarios": active_scenarios,
            "recent_calls_today": recent_calls,
            "dtmf_enabled_scenarios": dtmf_enabled_scenarios,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as exc:
        logger.error(f"Erreur lors de la récupération des métriques: {exc}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des métriques")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )






