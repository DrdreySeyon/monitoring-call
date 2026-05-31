import logging
from datetime import datetime
from typing import Optional

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session

from ari import perform_call
from config import settings
from database import SessionLocal
from models import Scenario

logger = logging.getLogger(__name__)

DAY_MAP = {
    "mon": "mon",
    "monday": "mon",
    "lundi": "mon",
    "tue": "tue",
    "tuesday": "tue",
    "mardi": "tue",
    "wed": "wed",
    "wednesday": "wed",
    "mercredi": "wed",
    "thu": "thu",
    "thursday": "thu",
    "jeudi": "thu",
    "fri": "fri",
    "friday": "fri",
    "vendredi": "fri",
    "sat": "sat",
    "saturday": "sat",
    "samedi": "sat",
    "sun": "sun",
    "sunday": "sun",
    "dimanche": "sun",
}


def _build_scheduler() -> BackgroundScheduler:
    if settings.scheduler_jobstore_enabled:
        return BackgroundScheduler(
            timezone=settings.scheduler_timezone,
            jobstores={"default": SQLAlchemyJobStore(url=settings.database_url)},
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
        )

    return BackgroundScheduler(
        timezone=settings.scheduler_timezone,
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
    )


scheduler = _build_scheduler()


def scenario_job_id(scenario_id: int) -> str:
    return f"scenario_{scenario_id}"


def serialize_dt(value):
    return value.isoformat() if value else None


def scenario_to_schedule_dict(scenario: Scenario) -> dict:
    job = scheduler.get_job(scenario_job_id(scenario.id)) if scheduler.running else None
    next_run_at = job.next_run_time if job else scenario.next_run_at

    return {
        "id": scenario.id,
        "schedule_enabled": bool(scenario.schedule_enabled),
        "schedule_type": scenario.schedule_type,
        "schedule_time": scenario.schedule_time,
        "schedule_day_of_week": scenario.schedule_day_of_week,
        "schedule_date": scenario.schedule_date,
        "schedule_timezone": scenario.schedule_timezone or settings.scheduler_timezone,
        "prevent_overlap": bool(scenario.prevent_overlap),
        "retry_enabled": bool(scenario.retry_enabled),
        "last_run_at": serialize_dt(scenario.last_run_at),
        "last_run_status": scenario.last_run_status,
        "last_run_error": scenario.last_run_error,
        "next_run_at": serialize_dt(next_run_at),
        "job_id": scenario_job_id(scenario.id),
        "job_registered": bool(job),
    }


def parse_time(schedule_time: Optional[str]) -> tuple[int, int]:
    value = schedule_time or "08:00"
    hour, minute = value.split(":")
    return int(hour), int(minute)


def build_trigger(scenario: Scenario):
    schedule_type = scenario.schedule_type or scenario.frequency
    hour, minute = parse_time(scenario.schedule_time)
    timezone = scenario.schedule_timezone or settings.scheduler_timezone

    if schedule_type == "once":
        if not scenario.schedule_date:
            raise ValueError("schedule_date est obligatoire pour une planification once")
        run_date = datetime.fromisoformat(scenario.schedule_date)
        return DateTrigger(run_date=run_date, timezone=timezone)

    if schedule_type == "daily":
        return CronTrigger(hour=hour, minute=minute, timezone=timezone)

    if schedule_type == "weekly":
        day = (scenario.schedule_day_of_week or "mon").strip().lower()
        return CronTrigger(day_of_week=DAY_MAP.get(day, day), hour=hour, minute=minute, timezone=timezone)

    if schedule_type == "monthly":
        return CronTrigger(day=1, hour=hour, minute=minute, timezone=timezone)

    raise ValueError("Type de planification invalide")


def run_scenario_job(scenario_id: int, manual: bool = False) -> dict:
    db: Session = SessionLocal()

    try:
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            return {"status": "skipped", "message": "Scenario introuvable"}

        if not scenario.active:
            scenario.last_run_at = datetime.utcnow()
            scenario.last_run_status = "skipped"
            scenario.last_run_error = "Scenario inactif"
            db.commit()
            return {"status": "skipped", "message": "Scenario inactif"}

        if scenario.prevent_overlap:
            running_call = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if running_call and scenario.last_run_status == "running":
                return {"status": "skipped", "message": "Execution deja en cours"}

        scenario.last_run_at = datetime.utcnow()
        scenario.last_run_status = "running"
        scenario.last_run_error = None
        db.commit()

        call_row, ari_response = perform_call(
            db=db,
            caller=scenario.caller,
            callee=scenario.callee,
            trunk=scenario.trunk,
            call_time_s=scenario.call_time_s,
            dtmf=scenario.dtmf,
            time_s_before_dtmf=scenario.time_s_before_dtmf,
            time_ms_between_dtmf=scenario.time_ms_between_dtmf,
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            scenario_keyword=scenario.keyword,
            scenario_category=scenario.category,
        )

        scenario.last_run_at = datetime.utcnow()
        scenario.last_run_status = "success"
        scenario.last_run_error = None
        update_next_run_in_db(db, scenario)
        db.commit()

        return {
            "status": "success",
            "manual": manual,
            "scenario_id": scenario_id,
            "call_id": call_row.id,
            "channel_id": call_row.channel_id,
            "ari_response": ari_response,
        }

    except Exception as exc:
        logger.error("Erreur execution scenario planifie %s: %s", scenario_id, exc)
        scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if scenario:
            scenario.last_run_at = datetime.utcnow()
            scenario.last_run_status = "failed"
            scenario.last_run_error = str(exc)
            update_next_run_in_db(db, scenario)
            db.commit()
        return {"status": "failed", "scenario_id": scenario_id, "error": str(exc)}

    finally:
        db.close()


def register_scenario_job(scenario: Scenario) -> Optional[dict]:
    job_id = scenario_job_id(scenario.id)
    remove_scenario_job(scenario.id)

    schedule_type = scenario.schedule_type or scenario.frequency
    if not scenario.active or not scenario.schedule_enabled or not schedule_type:
        scenario.next_run_at = None
        return None

    trigger = build_trigger(scenario)
    job = scheduler.add_job(
        run_scenario_job,
        trigger=trigger,
        args=[scenario.id],
        id=job_id,
        name=f"{scenario.name} ({scenario.id})",
        replace_existing=True,
    )
    scenario.next_run_at = job.next_run_time
    return {"job_id": job.id, "next_run_at": serialize_dt(job.next_run_time)}


def remove_scenario_job(scenario_id: int) -> None:
    job_id = scenario_job_id(scenario_id)
    if scheduler.running and scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


def sync_scenario_job(db: Session, scenario: Scenario) -> Optional[dict]:
    result = register_scenario_job(scenario)
    update_next_run_in_db(db, scenario)
    db.commit()
    return result


def update_next_run_in_db(db: Session, scenario: Scenario) -> None:
    job = scheduler.get_job(scenario_job_id(scenario.id)) if scheduler.running else None
    scenario.next_run_at = job.next_run_time if job else None
    db.add(scenario)


def sync_all_scenario_jobs() -> None:
    db: Session = SessionLocal()
    try:
        scenarios = db.query(Scenario).all()
        for scenario in scenarios:
            try:
                register_scenario_job(scenario)
            except Exception as exc:
                logger.error("Erreur enregistrement job scenario %s: %s", scenario.id, exc)
                scenario.last_run_status = "schedule_error"
                scenario.last_run_error = str(exc)
        db.commit()
    finally:
        db.close()


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        logger.info("Scheduler desactive par configuration")
        return

    if not scheduler.running:
        scheduler.start()

    sync_all_scenario_jobs()
    logger.info("Scheduler demarre avec %s job(s)", len(scheduler.get_jobs()))


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def get_scheduler_status() -> dict:
    jobs = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": serialize_dt(job.next_run_time),
            })

    return {
        "enabled": settings.scheduler_enabled,
        "running": scheduler.running,
        "timezone": settings.scheduler_timezone,
        "job_count": len(jobs),
        "jobs": jobs,
    }
