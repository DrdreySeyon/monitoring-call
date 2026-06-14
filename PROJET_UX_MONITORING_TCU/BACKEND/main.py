from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


API_PREFIX = "/api"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(
    title="Monitoring d'Appels TCU - Backend UX",
    description="Backend de demonstration pour valider le nouveau rendu front AMI/CDR/Vosk.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScenarioCreate(BaseModel):
    name: str
    keyword: str
    category: str
    caller: str
    callee: str
    trunk: str
    call_time_s: int
    dtmf: str | None = None
    frequency: str | None = None
    start_at: str | None = None
    active: int = 1


CALLS: list[dict[str, Any]] = [
    {
        "id": 522,
        "endpoint": "PJSIP/TRUNK_SBC_SFR",
        "caller": "+33123456789",
        "callee": "+33752049226",
        "trunk": "TRUNK_SBC_SFR",
        "channel_id": "1781271300.546",
        "call_time_s": 30,
        "duration": 40,
        "hangup_cause": 16,
        "hangup_cause_detail": "Normal Clearing",
        "sip_error_code": None,
        "dtmf": "#12",
        "status": "answered",
        "status_label": "Decroche",
        "error_message": None,
        "scenario_id": 45,
        "scenario_name": "Ivan",
        "scenario_keyword": "bonjour, aide",
        "scenario_category": "SAV",
        "vosk_status": "OK",
        "transcription": "Bonjour, j'ai besoin d'aide pour mon dossier.",
        "keyword_expected": "bonjour, aide",
        "keyword_detected": "bonjour, aide",
        "keyword_status": "OK",
        "recording_path": "/srv/asterisk/var/spool/recording/1781271300.546.wav",
        "speech_checked_at": "2026-06-12T15:35:50",
        "speech_error": None,
        "cdr_disposition": "ANSWERED",
        "cdr_billsec": 38,
        "created_at": "2026-06-12T15:35:43",
        "keyword_checks": [
            {"keyword": "bonjour", "status": "OK"},
            {"keyword": "aide", "status": "OK"},
        ],
        "voicemail_checks": [],
    },
    {
        "id": 521,
        "endpoint": "PJSIP/C_SFR_SIRIUS",
        "caller": "+33111111111",
        "callee": "+33622222222",
        "trunk": "C_SFR_SIRIUS",
        "channel_id": "1781269335.540",
        "call_time_s": 30,
        "duration": 0,
        "hangup_cause": 19,
        "hangup_cause_detail": "No Answer",
        "sip_error_code": None,
        "dtmf": "#41",
        "status": "missed",
        "status_label": "Non decroche",
        "error_message": "Non decroche (CDR)",
        "scenario_id": 44,
        "scenario_name": "NMS",
        "scenario_keyword": "ivan",
        "scenario_category": "GSO",
        "vosk_status": "KO",
        "transcription": "",
        "keyword_expected": "ivan",
        "keyword_detected": None,
        "keyword_status": "KO",
        "recording_path": None,
        "speech_checked_at": None,
        "speech_error": None,
        "cdr_disposition": "NO ANSWER",
        "cdr_billsec": 0,
        "created_at": "2026-06-12T15:02:15",
        "keyword_checks": [{"keyword": "ivan", "status": "KO"}],
        "voicemail_checks": [],
    },
    {
        "id": 520,
        "endpoint": "PJSIP/C_SFR_VEGA",
        "caller": "+33123456789",
        "callee": "+33700000000",
        "trunk": "C_SFR_VEGA",
        "channel_id": "1781262300.534",
        "call_time_s": 20,
        "duration": 22,
        "hangup_cause": 16,
        "hangup_cause_detail": "Normal Clearing",
        "sip_error_code": None,
        "dtmf": None,
        "status": "answered",
        "status_label": "Decroche",
        "error_message": None,
        "scenario_id": 43,
        "scenario_name": "Controle messagerie",
        "scenario_keyword": "outils, monitoring",
        "scenario_category": "TEST",
        "vosk_status": "VOICEMAIL",
        "transcription": "Vous etes bien sur la messagerie vocale, veuillez laisser un message.",
        "keyword_expected": "outils, monitoring",
        "keyword_detected": "monitoring",
        "keyword_status": "KO",
        "recording_path": "/srv/asterisk/var/spool/recording/1781262300.534.wav",
        "speech_checked_at": "2026-06-12T14:56:30",
        "speech_error": None,
        "cdr_disposition": "ANSWERED",
        "cdr_billsec": 20,
        "created_at": "2026-06-12T14:56:22",
        "keyword_checks": [
            {"keyword": "outils", "status": "KO"},
            {"keyword": "monitoring", "status": "OK"},
        ],
        "voicemail_checks": [{"keyword": "messagerie vocale", "status": "OK"}],
    },
    {
        "id": 519,
        "endpoint": "PJSIP/TRUNK_SBC_SFR",
        "caller": "+33123456789",
        "callee": "+33999999999",
        "trunk": "TRUNK_SBC_SFR",
        "channel_id": None,
        "call_time_s": 15,
        "duration": 0,
        "hangup_cause": 34,
        "hangup_cause_detail": "No Circuit Available",
        "sip_error_code": 503,
        "dtmf": None,
        "status": "trunk_error",
        "status_label": "Erreur trunk",
        "error_message": "SIP 503 - No Circuit Available",
        "scenario_id": 42,
        "scenario_name": "Test trunk",
        "scenario_keyword": "test",
        "scenario_category": "TECH",
        "vosk_status": "KO",
        "transcription": "",
        "keyword_expected": "test",
        "keyword_detected": None,
        "keyword_status": "KO",
        "recording_path": None,
        "speech_checked_at": None,
        "speech_error": "Pas d'audio exploitable",
        "cdr_disposition": "FAILED",
        "cdr_billsec": 0,
        "created_at": "2026-06-12T13:46:06",
        "keyword_checks": [{"keyword": "test", "status": "KO"}],
        "voicemail_checks": [],
    },
]


SCENARIOS: list[dict[str, Any]] = [
    {
        "id": 45,
        "name": "Ivan",
        "keyword": "bonjour, aide",
        "category": "SAV",
        "caller": "+33123456789",
        "callee": "+33752049226",
        "trunk": "TRUNK_SBC_SFR",
        "call_time_s": 30,
        "dtmf": "#12",
        "frequency": "weekly",
        "active": 1,
        "created_at": "2026-06-08T10:00:00",
    },
    {
        "id": 43,
        "name": "Controle messagerie",
        "keyword": "outils, monitoring",
        "category": "TEST",
        "caller": "+33123456789",
        "callee": "+33700000000",
        "trunk": "C_SFR_VEGA",
        "call_time_s": 20,
        "dtmf": None,
        "frequency": "daily",
        "active": 1,
        "created_at": "2026-06-08T10:15:00",
    },
]


JOBS: list[dict[str, Any]] = [
    {
        "id": "scenario_45",
        "scenario_id": 45,
        "scenario_name": "Ivan",
        "frequency": "weekly",
        "next_run_time": "2026-06-19T14:30:00+02:00",
        "active": True,
    },
    {
        "id": "scenario_43",
        "scenario_id": 43,
        "scenario_name": "Controle messagerie",
        "frequency": "daily",
        "next_run_time": "2026-06-15T09:00:00+02:00",
        "active": True,
    },
]


@app.get("/")
def frontend() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "index.html")


app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "assets"), name="assets")


@app.get(f"{API_PREFIX}")
def api_root() -> dict[str, Any]:
    return {
        "name": "Monitoring d'Appels TCU - Backend UX",
        "status": "ok",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.get(f"{API_PREFIX}/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(f"{API_PREFIX}/health/detailed")
def health_detailed() -> dict[str, Any]:
    return {
        "api": {"status": "ok", "mode": "demo"},
        "database": {"status": "ok", "engine": "in-memory demo"},
        "ari": {"status": "ok", "url": "http://IP_ASTERISK:8088/ari"},
        "ami": {"enabled": True, "connected": True, "host": "IP_ASTERISK", "port": 5039, "status": "connected"},
        "scheduler": {"status": "ok", "jobs": len(JOBS)},
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.get(f"{API_PREFIX}/calls/history")
def calls_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": CALLS[start:end],
        "total": len(CALLS),
        "page": page,
        "page_size": page_size,
    }


@app.get(f"{API_PREFIX}/calls/stats")
def calls_stats() -> dict[str, Any]:
    return {
        "total": len(CALLS),
        "answered": sum(1 for call in CALLS if call["status"] == "answered"),
        "missed": sum(1 for call in CALLS if call["status"] == "missed"),
        "trunk_errors": sum(1 for call in CALLS if call["status"] == "trunk_error"),
        "keyword_ok": sum(1 for call in CALLS if call["vosk_status"] == "OK"),
        "voicemail": sum(1 for call in CALLS if call["vosk_status"] == "VOICEMAIL"),
    }


@app.get(f"{API_PREFIX}/calls/{{call_id}}")
def call_detail(call_id: int) -> dict[str, Any]:
    call = next((item for item in CALLS if item["id"] == call_id), None)
    if not call:
        raise HTTPException(status_code=404, detail="Appel introuvable")
    return call


@app.get(f"{API_PREFIX}/vosk/results")
def vosk_results(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
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


@app.get(f"{API_PREFIX}/scenarios")
def scenarios() -> list[dict[str, Any]]:
    return SCENARIOS


@app.post(f"{API_PREFIX}/scenarios")
def create_scenario(payload: ScenarioCreate) -> dict[str, Any]:
    next_id = max((scenario["id"] for scenario in SCENARIOS), default=0) + 1
    scenario = {
        "id": next_id,
        "name": payload.name,
        "keyword": payload.keyword,
        "category": payload.category,
        "caller": payload.caller,
        "callee": payload.callee,
        "trunk": payload.trunk,
        "call_time_s": payload.call_time_s,
        "dtmf": payload.dtmf,
        "frequency": payload.frequency,
        "start_at": payload.start_at,
        "active": payload.active,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    SCENARIOS.insert(0, scenario)
    return scenario


@app.put(f"{API_PREFIX}/scenarios/{{scenario_id}}")
def update_scenario(scenario_id: int, payload: ScenarioCreate) -> dict[str, Any]:
    scenario = next((item for item in SCENARIOS if item["id"] == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario introuvable")
    scenario.update(
        {
            "name": payload.name,
            "keyword": payload.keyword,
            "category": payload.category,
            "caller": payload.caller,
            "callee": payload.callee,
            "trunk": payload.trunk,
            "call_time_s": payload.call_time_s,
            "dtmf": payload.dtmf,
            "frequency": payload.frequency,
            "start_at": payload.start_at,
            "active": payload.active,
        }
    )
    return scenario


@app.delete(f"{API_PREFIX}/scenarios/{{scenario_id}}")
def delete_scenario(scenario_id: int) -> dict[str, Any]:
    index = next((idx for idx, item in enumerate(SCENARIOS) if item["id"] == scenario_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Scenario introuvable")
    deleted = SCENARIOS.pop(index)
    return {"deleted": True, "id": deleted["id"]}


@app.post(f"{API_PREFIX}/scenarios/{{scenario_id}}/toggle")
def toggle_scenario(scenario_id: int) -> dict[str, Any]:
    scenario = next((item for item in SCENARIOS if item["id"] == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario introuvable")
    scenario["active"] = 0 if int(scenario.get("active") or 0) else 1
    return scenario


@app.post(f"{API_PREFIX}/scenarios/{{scenario_id}}/run-now")
def run_scenario_now(scenario_id: int) -> dict[str, Any]:
    scenario = next((item for item in SCENARIOS if item["id"] == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario introuvable")
    return {
        "started": True,
        "scenario_id": scenario_id,
        "scenario_name": scenario["name"],
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.get(f"{API_PREFIX}/scheduler/status")
def scheduler_status() -> dict[str, Any]:
    return {"enabled": True, "status": "running", "jobs": len(JOBS), "timezone": "Europe/Paris"}


@app.get(f"{API_PREFIX}/scheduler/jobs")
def scheduler_jobs() -> list[dict[str, Any]]:
    return JOBS


@app.post(f"{API_PREFIX}/scheduler/jobs/{{job_id}}/toggle")
def toggle_scheduler_job(job_id: str) -> dict[str, Any]:
    job = next((item for item in JOBS if item["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    job["active"] = not bool(job.get("active"))
    return job


@app.post(f"{API_PREFIX}/scheduler/jobs/{{job_id}}/run-now")
def run_scheduler_job(job_id: str) -> dict[str, Any]:
    job = next((item for item in JOBS if item["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return {"started": True, "job_id": job_id, "scenario_id": job.get("scenario_id")}
