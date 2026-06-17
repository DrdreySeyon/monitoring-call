from pydantic import BaseModel


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
