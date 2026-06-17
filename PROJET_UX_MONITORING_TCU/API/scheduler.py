from config import settings
from database import JOBS, find_job


def get_scheduler_status():
    return {
        "enabled": True,
        "status": "running",
        "jobs": len(JOBS),
        "timezone": settings.scheduler_timezone,
    }


def list_scheduler_jobs():
    return JOBS


def toggle_scheduler_job(job_id: str):
    job = find_job(job_id)
    if not job:
        return None
    job["active"] = not bool(job.get("active"))
    return job


def run_scheduler_job(job_id: str):
    job = find_job(job_id)
    if not job:
        return None
    return {"started": True, "job_id": job_id, "scenario_id": job.get("scenario_id")}
