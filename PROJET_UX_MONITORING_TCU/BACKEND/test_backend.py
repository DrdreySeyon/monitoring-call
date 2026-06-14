from fastapi import HTTPException

from main import (
    ScenarioCreate,
    call_detail,
    calls_history,
    create_scenario,
    delete_scenario,
    health_detailed,
    run_scheduler_job,
    run_scenario_now,
    scheduler_jobs,
    scheduler_status,
    scenarios,
    toggle_scenario,
    toggle_scheduler_job,
    update_scenario,
    vosk_results,
)


def test_health_detailed():
    payload = health_detailed()
    assert payload["api"]["status"] == "ok"
    assert payload["ami"]["enabled"] is True
    assert payload["ami"]["connected"] is True


def test_calls_history_contains_call_and_business_status():
    payload = calls_history(page=1, page_size=10)
    assert payload["total"] >= 4
    first = payload["items"][0]
    assert first["status"] == "answered"
    assert first["vosk_status"] == "OK"
    assert first["hangup_cause_detail"] == "Normal Clearing"


def test_call_detail_not_found():
    try:
        call_detail(999999)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("call_detail aurait du retourner 404")


def test_vosk_results_include_voicemail_and_keyword_checks():
    payload = vosk_results(page=1, page_size=10)
    statuses = {item["vosk_status"] for item in payload["items"]}
    assert "OK" in statuses
    assert "KO" in statuses
    assert "VOICEMAIL" in statuses
    voicemail = next(item for item in payload["items"] if item["vosk_status"] == "VOICEMAIL")
    assert voicemail["voicemail_checks"][0]["status"] == "OK"
    assert any(check["keyword"] == "monitoring" for check in voicemail["keyword_checks"])


def test_scenarios_and_scheduler():
    scenario_rows = scenarios()
    jobs = scheduler_jobs()
    scheduler = scheduler_status()
    assert len(scenario_rows) >= 2
    assert len(jobs) >= 2
    assert scheduler["status"] == "running"


def test_create_scenario():
    before = len(scenarios())
    created = create_scenario(
        ScenarioCreate(
            name="Scenario test UX",
            keyword="alpha, beta",
            category="TEST",
            caller="+33100000000",
            callee="+33200000000",
            trunk="TRUNK_TEST",
            call_time_s=25,
            dtmf="#9",
            frequency="once",
            start_at="2026-06-14T14:00",
            active=1,
        )
    )
    assert created["id"]
    assert created["name"] == "Scenario test UX"
    assert len(scenarios()) == before + 1
    updated = update_scenario(
        created["id"],
        ScenarioCreate(
            name="Scenario test UX modifie",
            keyword="alpha",
            category="TEST",
            caller="+33100000000",
            callee="+33200000000",
            trunk="TRUNK_TEST",
            call_time_s=35,
            dtmf="#8",
            frequency="daily",
            start_at="2026-06-14T15:00",
            active=1,
        ),
    )
    assert updated["name"] == "Scenario test UX modifie"
    toggled = toggle_scenario(created["id"])
    assert toggled["active"] == 0
    run_result = run_scenario_now(created["id"])
    assert run_result["started"] is True
    deleted = delete_scenario(created["id"])
    assert deleted["deleted"] is True


def test_scheduler_actions():
    job = scheduler_jobs()[0]
    toggled = toggle_scheduler_job(job["id"])
    assert toggled["active"] is False
    run_result = run_scheduler_job(job["id"])
    assert run_result["started"] is True
    toggle_scheduler_job(job["id"])


if __name__ == "__main__":
    test_health_detailed()
    test_calls_history_contains_call_and_business_status()
    test_call_detail_not_found()
    test_vosk_results_include_voicemail_and_keyword_checks()
    test_scenarios_and_scheduler()
    test_create_scenario()
    test_scheduler_actions()
    print("OK - backend UX teste")
