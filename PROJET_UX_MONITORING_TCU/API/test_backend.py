from fastapi import HTTPException

from main import (
    call_detail,
    calls_history,
    create_scenario,
    delete_scenario,
    health_detailed,
    scenario_run_now,
    scheduler_job_run_now,
    scheduler_job_toggle,
    scheduler_jobs,
    scheduler_status,
    scenarios,
    toggle_scenario,
    update_scenario,
    vosk_results,
)
from models import ScenarioCreate


def scenario_payload(**overrides):
    payload = {
        "name": "Scenario test UX",
        "keyword": "alpha, beta",
        "category": "TEST",
        "caller": "+33100000000",
        "callee": "+33200000000",
        "trunk": "TRUNK_TEST",
        "call_time_s": 25,
        "dtmf": "#9",
        "frequency": "once",
        "start_at": "2026-06-14T14:00",
        "active": 1,
    }
    payload.update(overrides)
    return ScenarioCreate(**payload)


def test_health_detailed():
    payload = health_detailed()
    assert payload["api"]["status"] == "ok"
    assert payload["ami"]["connected"] is True


def test_calls_and_vosk():
    history = calls_history(page=1, page_size=10)
    assert history["total"] >= 4
    assert history["items"][0]["status"] == "answered"
    statuses = {item["vosk_status"] for item in vosk_results(page=1, page_size=10)["items"]}
    assert {"OK", "KO", "VOICEMAIL"}.issubset(statuses)


def test_not_found():
    try:
        call_detail(999999)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("call_detail aurait du retourner 404")


def test_scenario_crud_and_run():
    before = len(scenarios())
    created = create_scenario(scenario_payload())
    assert len(scenarios()) == before + 1
    updated = update_scenario(created["id"], scenario_payload(name="Scenario modifie"))
    assert updated["name"] == "Scenario modifie"
    toggled = toggle_scenario(created["id"])
    assert toggled["active"] == 0
    run_result = scenario_run_now(created["id"])
    assert run_result["started"] is True
    deleted = delete_scenario(created["id"])
    assert deleted["deleted"] is True


def test_scheduler():
    assert scheduler_status()["status"] == "running"
    job = scheduler_jobs()[0]
    toggled = scheduler_job_toggle(job["id"])
    assert toggled["active"] is False
    assert scheduler_job_run_now(job["id"])["started"] is True
    scheduler_job_toggle(job["id"])


if __name__ == "__main__":
    test_health_detailed()
    test_calls_and_vosk()
    test_not_found()
    test_scenario_crud_and_run()
    test_scheduler()
    print("OK - backend UX aligne teste")
