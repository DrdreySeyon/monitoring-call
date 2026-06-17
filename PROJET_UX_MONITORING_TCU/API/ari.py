from datetime import datetime

from database import find_scenario


def run_scenario_now(scenario_id: int):
    scenario = find_scenario(scenario_id)
    if not scenario:
        return None
    return {
        "started": True,
        "scenario_id": scenario_id,
        "scenario_name": scenario["name"],
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
