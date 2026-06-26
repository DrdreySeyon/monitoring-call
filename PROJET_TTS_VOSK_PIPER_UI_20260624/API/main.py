import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import re
import unicodedata

from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import and_, bindparam, func, or_, text
from scheduler import (
    get_scheduler_status,
    remove_scenario_job,
    run_scenario_job,
    scenario_to_schedule_dict,
    shutdown_scheduler,
    start_scheduler,
    sync_all_scenario_jobs,
    sync_scenario_job,
)

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
    test_ari_connection
)
from ami_listener import (
    is_ami_listener_running,
    start_ami_listener_background,
    stop_ami_listener_background,
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONT_ROOT = PROJECT_ROOT / "FRONT"

if FRONT_ROOT.exists():
    app.mount("/assets", StaticFiles(directory=FRONT_ROOT / "assets"), name="assets")

create_tables()


# ============================================================
# EXCEPTIONS
# ============================================================

@app.get("/")
def serve_front():
    index_path = FRONT_ROOT / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend UX introuvable")
    return FileResponse(index_path)

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
async def startup_event():
    logger.info("Démarrage du scheduler...")
    start_scheduler()  # Démarre les tâches programmées
    await start_ami_listener_background()
    logger.info("Scheduler démarré avec succès.")



@app.on_event("shutdown")
async def shutdown_event():
    await stop_ami_listener_background()
    shutdown_scheduler()


def serialize_scenario(s: Scenario) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "keyword": s.keyword,
        "category": s.category,
        "caller": s.caller,
        "callee": s.callee,
        "trunk": s.trunk,
        "call_time_s": s.call_time_s,
        "ring_timeout_s": s.ring_timeout_s or 60,
        "dtmf": s.dtmf,
        "time_s_before_dtmf": s.time_s_before_dtmf,
        "time_ms_between_dtmf": s.time_ms_between_dtmf,
        "tts": s.tts,
        "frequency": s.frequency,
        "active": bool(s.active),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "schedule": scenario_to_schedule_dict(s),
    }


def apply_schedule_fields(target: Scenario, source) -> None:
    target.schedule_enabled = 1 if getattr(source, "schedule_enabled", False) else 0
    target.schedule_type = getattr(source, "schedule_type", None) or getattr(source, "frequency", None)
    target.schedule_time = getattr(source, "schedule_time", None)
    target.schedule_day_of_week = getattr(source, "schedule_day_of_week", None)
    target.schedule_date = getattr(source, "schedule_date", None)
    target.schedule_timezone = getattr(source, "schedule_timezone", None)
    target.prevent_overlap = 1 if getattr(source, "prevent_overlap", True) else 0
    target.retry_enabled = 1 if getattr(source, "retry_enabled", False) else 0
    normalize_schedule_start(target)


def normalize_schedule_start(target: Scenario) -> None:
    schedule_type = target.schedule_type or target.frequency
    if not target.schedule_enabled or not schedule_type:
        return

    if not target.schedule_date:
        raise HTTPException(
            status_code=400,
            detail="La date et l'heure de debut sont obligatoires pour la planification",
        )

    try:
        start_at = datetime.fromisoformat(target.schedule_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="La date et l'heure de debut doivent etre au format ISO",
        )

    day_codes = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    target.schedule_time = f"{start_at.hour:02d}:{start_at.minute:02d}"
    target.schedule_day_of_week = day_codes[start_at.weekday()]


HANGUP_CAUSE_LABELS = {
    1: "Numero non attribue",
    2: "Pas de route vers le reseau",
    3: "Pas de route vers la destination",
    16: "Decroche / fin normale",
    17: "Occupe",
    18: "Pas de reponse utilisateur",
    19: "Non decroche",
    20: "Abonne absent",
    21: "Appel rejete",
    22: "Numero change",
    27: "Destination hors service",
    28: "Numero invalide",
    31: "Fin normale non specifiee",
    34: "Pas de circuit ou canal disponible",
    38: "Reseau hors service",
    41: "Echec temporaire",
    42: "Equipement sature",
    44: "Canal demande indisponible",
    47: "Ressource indisponible",
    57: "Bearer capability non autorisee",
    58: "Bearer capability indisponible",
    88: "Destination incompatible",
    102: "Expiration timer reseau",
    111: "Erreur protocole",
    127: "Interfonctionnement non specifie",
}

BUSY_HANGUP_CAUSES = {17}
NO_ANSWER_HANGUP_CAUSES = {18, 19, 20}
REJECTED_HANGUP_CAUSES = {21}
TRUNK_ERROR_HANGUP_CAUSES = {1, 2, 3, 22, 27, 28, 31, 34, 38, 41, 42, 44, 47, 57, 58, 88, 102, 111, 127}

CALL_STATUS_LABELS = {
    "answered": "Decroche / raccroche",
    "no_answer": "Non decroche",
    "busy": "Occupe",
    "rejected": "Rejete",
    "trunk_error": "Erreur trunk",
    "failed": "Echec appel",
    "in_progress": "En cours",
    "success": "Reussi",
}

CDR_ERROR_LABELS = {
    "BUSY": "Occupe (CDR)",
    "NO ANSWER": "Non decroche (CDR)",
    "NOANSWER": "Non decroche (CDR)",
    "CANCEL": "Appel annule (CDR)",
    "CANCELLED": "Appel annule (CDR)",
    "FAILED": "Echec appel (CDR)",
    "CONGESTION": "Congestion trunk (CDR)",
    "CHANUNAVAIL": "Canal indisponible (CDR)",
}

VOICEMAIL_MARKERS = (
    "messagerie",
    "boite vocale",
    "boîte vocale",
    "repondeur",
    "répondeur",
    "laissez un message",
    "laisser un message",
    "apres le bip",
    "après le bip",
    "apres le signal sonore",
    "après le signal sonore",
    "votre correspondant",
    "n'est pas disponible",
    "est indisponible",
)

VOICEMAIL_SQL_MARKERS = (
    "messagerie",
    "boite vocale",
    "boîte vocale",
    "repondeur",
    "répondeur",
    "laissez un message",
    "laisser un message",
    "apres le bip",
    "après le bip",
    "signal sonore",
    "votre correspondant",
    "pas disponible",
    "indisponible",
)


def get_hangup_cause_label(hangup_cause: Optional[int]) -> Optional[str]:
    if hangup_cause is None:
        return None
    return HANGUP_CAUSE_LABELS.get(int(hangup_cause), f"Cause inconnue ({hangup_cause})")


def safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_cdr_value(cdr_info: Optional[dict], key: str):
    if not cdr_info:
        return None
    return cdr_info.get(key)


def get_cdr_int(cdr_info: Optional[dict], key: str) -> Optional[int]:
    return safe_int(get_cdr_value(cdr_info, key))


def get_cdr_disposition(cdr_info: Optional[dict]) -> Optional[str]:
    disposition = get_cdr_value(cdr_info, "disposition")
    if not disposition:
        return None
    return str(disposition).strip().upper()


def has_answer_evidence(call: Call, cdr_info: Optional[dict] = None) -> bool:
    disposition = get_cdr_disposition(cdr_info)
    if disposition == "ANSWERED":
        return True
    billsec = get_cdr_int(cdr_info, "billsec")
    if billsec is not None and billsec > 0:
        return True
    return safe_int(call.hangup_cause) == 16


KEYWORD_SEPARATOR_RE = re.compile(r"[;,|\r\n]+")


def normalize_keyword_text(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(without_accents.split())


def is_voicemail_transcription(call: Call) -> bool:
    normalized_transcription = normalize_keyword_text(call.transcription)
    if not normalized_transcription:
        return False
    return any(normalize_keyword_text(marker) in normalized_transcription for marker in VOICEMAIL_MARKERS)


def get_effective_call_status(call: Call, cdr_info: Optional[dict] = None) -> Optional[str]:
    raw_status = (call.status or "").strip().lower()
    if raw_status == "in_progress":
        return "in_progress"

    disposition = get_cdr_disposition(cdr_info)
    if disposition == "BUSY":
        return "busy"
    if disposition in {"NO ANSWER", "NOANSWER", "CANCEL", "CANCELLED"}:
        return "no_answer"
    if disposition in {"FAILED", "CONGESTION", "CHANUNAVAIL"}:
        return "trunk_error"

    if has_answer_evidence(call, cdr_info):
        return "answered"

    hangup_cause = safe_int(call.hangup_cause)
    if hangup_cause in BUSY_HANGUP_CAUSES:
        return "busy"
    if hangup_cause in NO_ANSWER_HANGUP_CAUSES:
        return "no_answer"
    if hangup_cause in REJECTED_HANGUP_CAUSES:
        return "rejected"
    if hangup_cause in TRUNK_ERROR_HANGUP_CAUSES:
        return "trunk_error"

    if raw_status == "success":
        return "answered"
    if raw_status == "failed":
        return "failed"
    return raw_status or None


def get_effective_call_status_label(call: Call, cdr_info: Optional[dict] = None) -> Optional[str]:
    status = get_effective_call_status(call, cdr_info)
    if not status:
        return None
    return CALL_STATUS_LABELS.get(status, status)


def get_effective_call_status_reason(call: Call, cdr_info: Optional[dict] = None) -> Optional[str]:
    if call.hangup_cause_detail:
        if call.sip_error_code:
            return f"AMI: {call.hangup_cause_detail} / TechCause: {call.sip_error_code}"
        return f"AMI: {call.hangup_cause_detail}"

    disposition = get_cdr_disposition(cdr_info)
    if disposition:
        return f"CDR disposition: {disposition}"
    hangup_label = get_hangup_cause_label(call.hangup_cause)
    if hangup_label:
        return hangup_label
    return call.status


def split_expected_keywords(value: Optional[str]) -> list[str]:
    if not value:
        return []
    keywords = []
    seen = set()
    for raw_keyword in KEYWORD_SEPARATOR_RE.split(value):
        keyword = raw_keyword.strip()
        normalized = normalize_keyword_text(keyword)
        if keyword and normalized not in seen:
            keywords.append(keyword)
            seen.add(normalized)
    return keywords


def get_call_expected_keywords(call: Call) -> list[str]:
    return split_expected_keywords(call.keyword_expected or call.scenario_keyword)


def get_keyword_checks(call: Call) -> list[dict]:
    expected_keywords = get_call_expected_keywords(call)
    if not expected_keywords:
        return []

    normalized_transcription = normalize_keyword_text(call.transcription)
    checks = []
    for keyword in expected_keywords:
        normalized_keyword = normalize_keyword_text(keyword)
        found = bool(normalized_keyword and normalized_keyword in normalized_transcription)
        checks.append({
            "keyword": keyword,
            "status": "OK" if found else "KO",
            "found": found,
        })
    return checks


def get_voicemail_checks(call: Call) -> list[dict]:
    normalized_transcription = normalize_keyword_text(call.transcription)
    if not normalized_transcription:
        return []

    checks = []
    seen = set()
    for marker in VOICEMAIL_MARKERS:
        normalized_marker = normalize_keyword_text(marker)
        if not normalized_marker or normalized_marker in seen:
            continue
        seen.add(normalized_marker)
        found = normalized_marker in normalized_transcription
        if found:
            checks.append({
                "keyword": marker,
                "status": "OK",
                "found": True,
                "type": "voicemail",
            })
    return checks


def get_effective_vosk_status(call: Call) -> Optional[str]:
    if get_voicemail_checks(call):
        return "VOICEMAIL"

    keyword_checks = get_keyword_checks(call)
    if keyword_checks:
        return "OK" if all(item["found"] for item in keyword_checks) else "KO"
    return call.vosk_status


def get_ami_error_display(call: Call) -> Optional[str]:
    details = []
    if call.hangup_cause_detail:
        details.append(f"AMI: {call.hangup_cause_detail}")
    if call.sip_error_code:
        details.append(f"TechCause: {call.sip_error_code}")
    return " / ".join(details) if details else None


def get_call_error_display(call: Call, cdr_info: Optional[dict] = None) -> Optional[str]:
    if call.error_message:
        return call.error_message

    ami_error = get_ami_error_display(call)
    if ami_error:
        return ami_error

    effective_status = get_effective_call_status(call, cdr_info)
    if effective_status in {"answered", "in_progress"}:
        return None

    disposition = get_cdr_disposition(cdr_info)
    if disposition and disposition in CDR_ERROR_LABELS:
        return CDR_ERROR_LABELS[disposition]

    if call.hangup_cause is None or int(call.hangup_cause) == 16:
        return None
    return get_hangup_cause_label(call.hangup_cause)


def get_voicemail_sql_clause():
    return or_(*(Call.transcription.ilike(f"%{marker}%") for marker in VOICEMAIL_SQL_MARKERS))


def apply_effective_status_filter(query, status: Optional[str]):
    if not status:
        return query

    value = status.strip().lower()
    if value in {"success", "answered"}:
        return query.filter(
            or_(
                Call.hangup_cause == 16,
                and_(Call.hangup_cause.is_(None), Call.status == "success"),
            )
        )

    if value == "voicemail":
        return query.filter(and_(Call.transcription.isnot(None), get_voicemail_sql_clause()))

    if value == "no_answer":
        return query.filter(Call.hangup_cause.in_(tuple(NO_ANSWER_HANGUP_CAUSES)))

    if value == "busy":
        return query.filter(Call.hangup_cause.in_(tuple(BUSY_HANGUP_CAUSES)))

    if value == "rejected":
        return query.filter(Call.hangup_cause.in_(tuple(REJECTED_HANGUP_CAUSES)))

    if value == "trunk_error":
        return query.filter(Call.hangup_cause.in_(tuple(TRUNK_ERROR_HANGUP_CAUSES)))

    if value == "failed":
        return query.filter(
            or_(
                and_(Call.hangup_cause.isnot(None), Call.hangup_cause != 16),
                and_(Call.hangup_cause.is_(None), Call.status == "failed"),
            )
        )

    return query.filter(and_(Call.hangup_cause.is_(None), Call.status == value))


def fetch_cdr_details_map(channel_ids: list[str], db: Session) -> dict:
    unique_ids = list(dict.fromkeys(channel_id for channel_id in channel_ids if channel_id))
    if not unique_ids:
        return {}

    try:
        statement = text(
            "SELECT uniqueid, disposition, duration, billsec "
            "FROM cdr "
            "WHERE uniqueid IN :channel_ids "
            "ORDER BY calldate DESC"
        ).bindparams(bindparam("channel_ids", expanding=True))

        rows = db.execute(statement, {"channel_ids": unique_ids}).mappings().all()
    except Exception as exc:
        logger.warning(f"Erreur lors de la recuperation des details CDR: {exc}")
        return {}

    details = {}
    for row in rows:
        uniqueid = row.get("uniqueid")
        if uniqueid and uniqueid not in details:
            details[uniqueid] = {
                "disposition": row.get("disposition"),
                "duration": row.get("duration"),
                "billsec": row.get("billsec"),
            }
    return details


def serialize_call(call: Call, cdr_info: Optional[dict] = None) -> dict:
    effective_status = get_effective_call_status(call, cdr_info)
    error_display = get_call_error_display(call, cdr_info)
    effective_vosk_status = get_effective_vosk_status(call)
    keyword_checks = get_keyword_checks(call)
    voicemail_checks = get_voicemail_checks(call)
    return {
        "id": call.id,
        "endpoint": call.endpoint,
        "caller": call.caller,
        "callee": call.callee,
        "trunk": call.trunk,
        "channel_id": call.channel_id,
        "call_time_s": call.call_time_s,
        "ring_timeout_s": call.ring_timeout_s or 60,
        "duration": call.duration,
        "hangup_cause": call.hangup_cause,
        "hangup_cause_label": get_hangup_cause_label(call.hangup_cause),
        "hangup_cause_detail": call.hangup_cause_detail,
        "sip_error_code": call.sip_error_code,
        "dtmf": call.dtmf,
        "time_s_before_dtmf": call.time_s_before_dtmf,
        "time_ms_between_dtmf": call.time_ms_between_dtmf,
        "tts": call.tts,
        "status": effective_status,
        "status_label": get_effective_call_status_label(call, cdr_info),
        "status_reason": get_effective_call_status_reason(call, cdr_info),
        "raw_status": call.status,
        "cdr_disposition": get_cdr_disposition(cdr_info),
        "cdr_duration": get_cdr_int(cdr_info, "duration"),
        "cdr_billsec": get_cdr_int(cdr_info, "billsec"),
        "error_message": call.error_message,
        "error_display": error_display,
        "scenario_id": call.scenario_id,
        "scenario_name": call.scenario_name,
        "scenario_keyword": call.scenario_keyword,
        "scenario_category": call.scenario_category,
        "keyword_expected": call.keyword_expected,
        "keyword_detected": call.keyword_detected,
        "keyword_status": call.keyword_status,
        "vosk_status": effective_vosk_status,
        "raw_vosk_status": call.vosk_status,
        "transcription": call.transcription,
        "vosk_transcription": call.transcription,
        "keyword_checks": keyword_checks,
        "voicemail_detected": bool(voicemail_checks),
        "voicemail_checks": voicemail_checks,
        "vosk_result_created_at": call.created_at.isoformat() if call.created_at else None,
        "recording_path": call.recording_path,
        "speech_checked_at": call.speech_checked_at.isoformat() if call.speech_checked_at else None,
        "speech_error": call.speech_error,
        "created_at": call.created_at.isoformat() if call.created_at else None,
    }


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

    ami_check = {
        "status": "ok" if is_ami_listener_running() else ("disabled" if not settings.ami_enabled else "error"),
        "enabled": settings.ami_enabled,
        "running": is_ami_listener_running(),
        "host": settings.ami_host,
        "port": settings.ami_port,
    }
    health_status["checks"]["ami"] = ami_check
    if settings.ami_enabled and ami_check["status"] != "ok":
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
        ring_timeout_s=req.ring_timeout_s,
        dtmf=req.dtmf,
        time_s_before_dtmf=req.time_s_before_dtmf,
        time_ms_between_dtmf=req.time_ms_between_dtmf,
        tts=req.tts,
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
            "ring_timeout_s": call_row.ring_timeout_s or 60,
            "duration": call_row.duration,
            "hangup_cause": call_row.hangup_cause,
            "dtmf": call_row.dtmf,
            "time_s_before_dtmf": call_row.time_s_before_dtmf,
            "time_ms_between_dtmf": call_row.time_ms_between_dtmf,
            "tts": call_row.tts,
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
    query = apply_effective_status_filter(query, status)

    total = query.count()
    query = query.order_by(Call.created_at.desc(), Call.id.desc())

    offset = (page - 1) * page_size
    rows = query.offset(offset).limit(page_size).all()
    cdr_details_map = fetch_cdr_details_map([c.channel_id for c in rows], db)

    if include_duration:
        calls_without_duration = [
            c for c in rows
            if c.duration is None and c.channel_id
        ]

        if calls_without_duration:
            updated_calls = []
            for call in calls_without_duration:
                cdr_info = cdr_details_map.get(call.channel_id)
                cdr_duration = get_cdr_int(cdr_info, "duration")
                if cdr_duration is not None:
                    call.duration = cdr_duration
                    updated_calls.append(call)

            if updated_calls:
                try:
                    db.commit()
                except Exception as exc:
                    logger.error(f"Erreur lors de la mise à jour des durées: {exc}")
                    db.rollback()

    items = []
    for c in rows:
        items.append(serialize_call(c, cdr_details_map.get(c.channel_id)))

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
    query = apply_effective_status_filter(query, status)

    rows = query.all()
    cdr_details_map = fetch_cdr_details_map([call.channel_id for call in rows], db)

    data = []
    for call in rows:
        cdr_info = cdr_details_map.get(call.channel_id)
        data.append({
            "id": call.id,
            "caller": call.caller,
            "callee": call.callee,
            "status": get_effective_call_status(call, cdr_info),
            "status_label": get_effective_call_status_label(call, cdr_info),
            "status_reason": get_effective_call_status_reason(call, cdr_info),
            "raw_status": call.status,
            "cdr_disposition": get_cdr_disposition(cdr_info),
            "cdr_duration": get_cdr_int(cdr_info, "duration"),
            "cdr_billsec": get_cdr_int(cdr_info, "billsec"),
            "hangup_cause": call.hangup_cause,
            "hangup_cause_label": get_hangup_cause_label(call.hangup_cause),
            "hangup_cause_detail": call.hangup_cause_detail,
            "sip_error_code": call.sip_error_code,
            "error_display": get_call_error_display(call, cdr_info),
            "vosk_status": get_effective_vosk_status(call),
            "voicemail_detected": bool(get_voicemail_checks(call)),
            "voicemail_checks": get_voicemail_checks(call),
            "created_at": call.created_at.isoformat() if call.created_at else None,
        })

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

    cdr_info = fetch_cdr_details_map([call.channel_id], db).get(call.channel_id)

    if call.duration is None and call.channel_id:
        cdr_duration = get_cdr_int(cdr_info, "duration")
        if cdr_duration is not None:
            call.duration = cdr_duration
            db.commit()
            db.refresh(call)

    return serialize_call(call, cdr_info)


@app.get(f"{settings.api_prefix}/vosk/results")
def get_vosk_results(
    vosk_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="page et page_size doivent etre >= 1")
    if page_size > 100:
        raise HTTPException(status_code=400, detail="page_size ne peut pas depasser 100")

    query = db.query(Call).filter(
        or_(
            Call.vosk_status.isnot(None),
            and_(
                Call.transcription.isnot(None),
                or_(
                    and_(Call.keyword_expected.isnot(None), Call.keyword_expected != ""),
                    and_(Call.scenario_keyword.isnot(None), Call.scenario_keyword != ""),
                ),
            ),
        )
    )

    rows = (
        query.order_by(Call.created_at.desc(), Call.id.desc())
        .all()
    )
    if vosk_status:
        requested_status = vosk_status.strip().upper()
        rows = [
            row for row in rows
            if (get_effective_vosk_status(row) or "").strip().upper() == requested_status
        ]

    total = len(rows)
    page_rows = rows[(page - 1) * page_size:page * page_size]
    cdr_details_map = fetch_cdr_details_map([row.channel_id for row in page_rows], db)

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [
            {
                "id": row.id,
                "call_id": row.id,
                "channel_id": row.channel_id,
                "status": get_effective_call_status(row, cdr_details_map.get(row.channel_id)),
                "status_label": get_effective_call_status_label(row, cdr_details_map.get(row.channel_id)),
                "status_reason": get_effective_call_status_reason(row, cdr_details_map.get(row.channel_id)),
                "cdr_disposition": get_cdr_disposition(cdr_details_map.get(row.channel_id)),
                "cdr_duration": get_cdr_int(cdr_details_map.get(row.channel_id), "duration"),
                "cdr_billsec": get_cdr_int(cdr_details_map.get(row.channel_id), "billsec"),
                "hangup_cause": row.hangup_cause,
                "hangup_cause_label": get_hangup_cause_label(row.hangup_cause),
                "hangup_cause_detail": row.hangup_cause_detail,
                "sip_error_code": row.sip_error_code,
                "error_display": get_call_error_display(row, cdr_details_map.get(row.channel_id)),
                "vosk_status": get_effective_vosk_status(row),
                "raw_vosk_status": row.vosk_status,
                "transcription": row.transcription,
                "keyword_checks": get_keyword_checks(row),
                "voicemail_detected": bool(get_voicemail_checks(row)),
                "voicemail_checks": get_voicemail_checks(row),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in page_rows
        ],
    }


# ============================================================
# SCENARIOS
# ============================================================

@app.get(f"{settings.api_prefix}/scenarios")
def get_scenarios(page: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Scenario).order_by(Scenario.created_at.desc())

    if page is None:
        rows = query.all()
        return [serialize_scenario(s) for s in rows]

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
                "ring_timeout_s": s.ring_timeout_s or 60,
                "dtmf": s.dtmf,
                "time_s_before_dtmf": s.time_s_before_dtmf,
                "time_ms_between_dtmf": s.time_ms_between_dtmf,
                "tts": s.tts,
                "frequency": s.frequency,
                "schedule_enabled": bool(s.schedule_enabled),
                "schedule_type": s.schedule_type,
                "schedule_time": s.schedule_time,
                "schedule_day_of_week": s.schedule_day_of_week,
                "schedule_date": s.schedule_date,
                "schedule_timezone": s.schedule_timezone,
                "prevent_overlap": bool(s.prevent_overlap),
                "retry_enabled": bool(s.retry_enabled),
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
                    ring_timeout_s=item.get("ring_timeout_s", 60),
                    dtmf=item.get("dtmf"),
                    time_s_before_dtmf=item.get("time_s_before_dtmf"),
                    time_ms_between_dtmf=item.get("time_ms_between_dtmf", 3000),
                    tts=item.get("tts"),
                    frequency=item.get("frequency"),
                    schedule_enabled=1 if item.get("schedule_enabled", False) else 0,
                    schedule_type=item.get("schedule_type") or item.get("frequency"),
                    schedule_time=item.get("schedule_time"),
                    schedule_day_of_week=item.get("schedule_day_of_week"),
                    schedule_date=item.get("schedule_date"),
                    schedule_timezone=item.get("schedule_timezone"),
                    prevent_overlap=1 if item.get("prevent_overlap", True) else 0,
                    retry_enabled=1 if item.get("retry_enabled", False) else 0,
                    active=1 if item.get("active", True) else 0
                )

                db.add(db_scenario)
                created += 1

            except Exception as exc:
                errors.append(f"Ligne {idx}: {str(exc)}")

        db.commit()
        sync_all_scenario_jobs()

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
            ring_timeout_s=scenario.ring_timeout_s,
            dtmf=scenario.dtmf,
            time_s_before_dtmf=scenario.time_s_before_dtmf,
            time_ms_between_dtmf=scenario.time_ms_between_dtmf,
            tts=scenario.tts,
            frequency=scenario.frequency,
            active=1 if scenario.active else 0
        )
        apply_schedule_fields(db_scenario, scenario)

        db.add(db_scenario)
        db.commit()
        db.refresh(db_scenario)
        sync_scenario_job(db, db_scenario)
        db.refresh(db_scenario)

        return serialize_scenario(db_scenario)

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

    return serialize_scenario(scenario)


@app.get(f"{settings.api_prefix}/scenarios/{{scenario_id}}/config-check")
def check_scenario_config(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario non trouve")

    checks = [
        {"name": "Scenario actif", "status": "ok" if scenario.active else "ko", "detail": "Actif" if scenario.active else "Scenario inactif"},
        {"name": "Appelant", "status": "ok" if scenario.caller else "ko", "detail": scenario.caller or "Numero appelant manquant"},
        {"name": "Appele", "status": "ok" if scenario.callee else "ko", "detail": scenario.callee or "Numero appele manquant"},
        {"name": "Trunk", "status": "ok" if scenario.trunk else "ko", "detail": scenario.trunk or "Trunk manquant"},
        {"name": "Duree prevue", "status": "ok" if scenario.call_time_s and scenario.call_time_s > 0 else "ko", "detail": f"{scenario.call_time_s or 0}s"},
        {"name": "Timeout sonnerie", "status": "ok" if scenario.ring_timeout_s and scenario.ring_timeout_s >= 5 else "ko", "detail": f"{scenario.ring_timeout_s or 0}s"},
    ]

    schedule_type = scenario.schedule_type or scenario.frequency
    if schedule_type:
        checks.append({
            "name": "Planification",
            "status": "ok" if scenario.schedule_date else "ko",
            "detail": scenario.schedule_date or "Date et heure de debut manquantes",
        })

    ari_check = test_ari_connection()
    checks.append({
        "name": "Connexion ARI",
        "status": "ok" if ari_check.get("status") == "ok" else "ko",
        "detail": ari_check.get("message", "ARI non verifie"),
    })

    return {
        "scenario": serialize_scenario(scenario),
        "status": "ok" if all(check["status"] == "ok" for check in checks) else "ko",
        "checks": checks,
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
            if field in ("active", "schedule_enabled", "prevent_overlap", "retry_enabled"):
                setattr(db_scenario, field, 1 if value else 0)
            else:
                setattr(db_scenario, field, value)

        if "schedule_type" not in update_data and "frequency" in update_data:
            db_scenario.schedule_type = db_scenario.frequency

        normalize_schedule_start(db_scenario)

        db.commit()
        db.refresh(db_scenario)
        sync_scenario_job(db, db_scenario)
        db.refresh(db_scenario)

        return serialize_scenario(db_scenario)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Erreur lors de la mise à jour du scénario {scenario_id}: {exc}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du scénario")


@app.put(f"{settings.api_prefix}/scenarios/{{scenario_id}}")
async def replace_scenario(
    scenario_id: int,
    scenario_update: ScenarioPatch,
    db: Session = Depends(get_db)
):
    return await update_scenario(scenario_id, scenario_update, db)


@app.delete(f"{settings.api_prefix}/scenarios/{{scenario_id}}")
async def delete_scenario(scenario_id: int, db: Session = Depends(get_db)):
    db_scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")

    try:
        scenario_name = db_scenario.name
        remove_scenario_job(scenario_id)
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
        sync_scenario_job(db, db_scenario)
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
            ring_timeout_s=db_scenario.ring_timeout_s or 60,
            dtmf=db_scenario.dtmf,
            time_s_before_dtmf=db_scenario.time_s_before_dtmf,
            time_ms_between_dtmf=db_scenario.time_ms_between_dtmf,
            tts=db_scenario.tts,
        )

        # enrichissement historique
        call_row.scenario_id = db_scenario.id
        call_row.scenario_name = db_scenario.name
        call_row.scenario_keyword = db_scenario.keyword
        call_row.scenario_category = db_scenario.category
        call_row.keyword_expected = db_scenario.keyword
        call_row.keyword_status = "pending"

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
                "ring_timeout_s": call_row.ring_timeout_s or 60,
                "duration": call_row.duration,
                "dtmf": call_row.dtmf,
                "time_s_before_dtmf": call_row.time_s_before_dtmf,
                "time_ms_between_dtmf": call_row.time_ms_between_dtmf,
                "tts": call_row.tts,
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
# SCHEDULER
# ============================================================

@app.get(f"{settings.api_prefix}/scheduler/status")
def scheduler_status():
    return get_scheduler_status()


@app.get(f"{settings.api_prefix}/scheduler/jobs")
def scheduler_jobs(db: Session = Depends(get_db)):
    scenarios = db.query(Scenario).order_by(Scenario.created_at.desc()).all()
    return {
        "scheduler": get_scheduler_status(),
        "items": [
            {
                "scenario": serialize_scenario(scenario),
                "schedule": scenario_to_schedule_dict(scenario),
            }
            for scenario in scenarios
        ],
    }


def scenario_id_from_job_id(job_id: str) -> int:
    if job_id.startswith("scenario_"):
        job_id = job_id.split("_", 1)[1]
    try:
        return int(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Identifiant de job invalide")


@app.post(f"{settings.api_prefix}/scheduler/jobs/{{job_id}}/toggle")
def toggle_scheduler_job(job_id: str, db: Session = Depends(get_db)):
    scenario_id = scenario_id_from_job_id(job_id)
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario introuvable")

    scenario.schedule_enabled = 0 if scenario.schedule_enabled else 1
    db.commit()
    db.refresh(scenario)
    sync_scenario_job(db, scenario)
    db.refresh(scenario)

    return {
        "id": f"scenario_{scenario.id}",
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "frequency": scenario.schedule_type or scenario.frequency,
        "next_run_time": scenario.next_run_at.isoformat() if scenario.next_run_at else None,
        "active": bool(scenario.schedule_enabled),
    }


@app.post(f"{settings.api_prefix}/scheduler/jobs/{{job_id}}/run-now")
def run_scheduler_job_now(job_id: str):
    scenario_id = scenario_id_from_job_id(job_id)
    result = run_scenario_job(scenario_id, manual=True)
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Execution echouee"))
    return result


@app.post(f"{settings.api_prefix}/scheduler/sync")
def scheduler_sync():
    sync_all_scenario_jobs()
    return get_scheduler_status()


@app.post(f"{settings.api_prefix}/scenarios/{{scenario_id}}/run-now")
def run_scenario_now(scenario_id: int):
    result = run_scenario_job(scenario_id, manual=True)
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Execution echouee"))
    return result


@app.post(f"{settings.api_prefix}/scenarios/{{scenario_id}}/schedule/sync")
def sync_one_scenario_schedule(scenario_id: int, db: Session = Depends(get_db)):
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario non trouve")

    sync_scenario_job(db, scenario)
    db.refresh(scenario)
    return serialize_scenario(scenario)


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
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )






