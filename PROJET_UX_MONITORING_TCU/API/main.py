from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ami_listener import get_ami_status
from ari import run_scenario_now
from config import settings
from database import CALLS, SCENARIOS, find_call, find_scenario
from models import ScenarioCreate
from scheduler import get_scheduler_status, list_scheduler_jobs, run_scheduler_job, toggle_scheduler_job


PROJECT_ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(title=settings.app_name, version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def frontend():
    return FileResponse(PROJECT_ROOT / "FRONT" / "index.html")


app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "FRONT" / "assets"), name="assets")


@app.get(f"{settings.api_prefix}")
def api_root():
    return {"name": settings.app_name, "status": "ok", "generated_at": datetime.now().isoformat(timespec="seconds")}


@app.get(f"{settings.api_prefix}/health")
def health():
    return {"status": "ok"}


@app.get(f"{settings.api_prefix}/health/detailed")
def health_detailed():
    scheduler_status = get_scheduler_status()
    return {
        "api": {"status": "ok", "mode": settings.api_mode},
        "database": {"status": "ok", "engine": settings.database_engine},
        "ari": {"status": "ok", "url": settings.ari_url},
        "ami": get_ami_status(),
        "scheduler": {"status": scheduler_status["status"], "jobs": scheduler_status["jobs"]},
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.get(f"{settings.api_prefix}/calls/history")
def calls_history(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=100)):
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": CALLS[start:end], "total": len(CALLS), "page": page, "page_size": page_size}


@app.get(f"{settings.api_prefix}/calls/stats")
def calls_stats():
    return {
        "total": len(CALLS),
        "answered": sum(1 for call in CALLS if call["status"] == "answered"),
        "missed": sum(1 for call in CALLS if call["status"] == "missed"),
        "trunk_errors": sum(1 for call in CALLS if call["status"] == "trunk_error"),
        "keyword_ok": sum(1 for call in CALLS if call["vosk_status"] == "OK"),
        "voicemail": sum(1 for call in CALLS if call["vosk_status"] == "VOICEMAIL"),
    }


@app.get(f"{settings.api_prefix}/calls/{{call_id}}")
def call_detail(call_id: int):
    call = find_call(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Appel introuvable")
    return call


@app.get(f"{settings.api_prefix}/vosk/results")
def vosk_results(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=100)):
    rows = [
        {
            "call_id": call["id"],
            "scenario_name": call["scenario_name"],
            "vosk_status": call["vosk_status"],
            "transcription": call["transcription"],
            "keyword_expected": call["keyword_expected"],
            "keyword_detected": call["keyword_detected"],
            "keyword_checks": call["keyword_checks"],
            "voicemail_checks": call["voicemail_checks"],
            "created_at": call["created_at"],
        }
        for call in CALLS
    ]
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": rows[start:end], "total": len(rows), "page": page, "page_size": page_size}


@app.get(f"{settings.api_prefix}/scenarios")
def scenarios():
    return SCENARIOS


@app.post(f"{settings.api_prefix}/scenarios")
def create_scenario(payload: ScenarioCreate):
    next_id = max((scenario["id"] for scenario in SCENARIOS), default=0) + 1
    scenario = payload.model_dump()
    scenario.update({"id": next_id, "created_at": datetime.now().isoformat(timespec="seconds")})
    SCENARIOS.insert(0, scenario)
    return scenario


@app.put(f"{settings.api_prefix}/scenarios/{{scenario_id}}")
def update_scenario(scenario_id: int, payload: ScenarioCreate):
    scenario = find_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario introuvable")
    scenario.update(payload.model_dump())
    return scenario


@app.delete(f"{settings.api_prefix}/scenarios/{{scenario_id}}")
def delete_scenario(scenario_id: int):
    index = next((idx for idx, item in enumerate(SCENARIOS) if item["id"] == scenario_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Scenario introuvable")
    deleted = SCENARIOS.pop(index)
    return {"deleted": True, "id": deleted["id"]}


@app.post(f"{settings.api_prefix}/scenarios/{{scenario_id}}/toggle")
def toggle_scenario(scenario_id: int):
    scenario = find_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario introuvable")
    scenario["active"] = 0 if int(scenario.get("active") or 0) else 1
    return scenario


@app.post(f"{settings.api_prefix}/scenarios/{{scenario_id}}/run-now")
def scenario_run_now(scenario_id: int):
    result = run_scenario_now(scenario_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scenario introuvable")
    return result


@app.get(f"{settings.api_prefix}/scheduler/status")
def scheduler_status():
    return get_scheduler_status()


@app.get(f"{settings.api_prefix}/scheduler/jobs")
def scheduler_jobs():
    return list_scheduler_jobs()


@app.post(f"{settings.api_prefix}/scheduler/jobs/{{job_id}}/toggle")
def scheduler_job_toggle(job_id: str):
    job = toggle_scheduler_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return job


@app.post(f"{settings.api_prefix}/scheduler/jobs/{{job_id}}/run-now")
def scheduler_job_run_now(job_id: str):
    result = run_scheduler_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return result
