import re
from typing import Optional

from pydantic import BaseModel, validator
from sqlalchemy import Column, Integer, String, DateTime, func, Text
from database import Base


# ============================================================
# MODELES SQLALCHEMY
# ============================================================

class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(255), nullable=False)
    caller = Column(String(64), nullable=False, index=True)
    callee = Column(String(64), nullable=False, index=True)
    trunk = Column(String(128), nullable=False)
    channel_id = Column(String(64), nullable=True, index=True)

    call_time_s = Column(Integer, nullable=False, default=30)
    duration = Column(Integer, nullable=True)
    hangup_cause = Column(Integer, nullable=True)
    hangup_cause_detail = Column(String(255), nullable=True)
    sip_error_code = Column(String(64), nullable=True)
    dtmf = Column(String(32), nullable=True)
    time_s_before_dtmf = Column(Integer, nullable=True)
    time_ms_between_dtmf = Column(Integer, nullable=True)

    status = Column(String(32), nullable=True, default="in_progress")
    error_message = Column(Text, nullable=True)

    scenario_id = Column(Integer, nullable=True, index=True)
    scenario_name = Column(String(255), nullable=True)
    scenario_keyword = Column(String(255), nullable=True)
    scenario_category = Column(String(255), nullable=True)
    keyword_expected = Column(String(255), nullable=True)
    keyword_detected = Column(String(255), nullable=True)
    keyword_status = Column(String(32), nullable=True)
    vosk_status = Column(String(32), nullable=True, index=True)
    transcription = Column(Text, nullable=True)
    recording_path = Column(String(1024), nullable=True)
    speech_checked_at = Column(DateTime(timezone=True), nullable=True)
    speech_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    keyword = Column(String(255), nullable=False, index=True)
    category = Column(String(255), nullable=False, index=True)
    caller = Column(String(64), nullable=False)
    callee = Column(String(64), nullable=False)
    trunk = Column(String(128), nullable=False)

    call_time_s = Column(Integer, nullable=False, default=30)
    dtmf = Column(String(32), nullable=True)
    time_s_before_dtmf = Column(Integer, nullable=True)
    time_ms_between_dtmf = Column(Integer, nullable=True, default=3000)

    frequency = Column(String(128), nullable=True)
    schedule_enabled = Column(Integer, nullable=False, default=0)
    schedule_type = Column(String(32), nullable=True)
    schedule_time = Column(String(8), nullable=True)
    schedule_day_of_week = Column(String(16), nullable=True)
    schedule_date = Column(String(32), nullable=True)
    schedule_timezone = Column(String(64), nullable=True)
    prevent_overlap = Column(Integer, nullable=False, default=1)
    retry_enabled = Column(Integer, nullable=False, default=0)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(32), nullable=True)
    last_run_error = Column(Text, nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# VALIDATEURS COMMUNS
# ============================================================

PHONE_REGEX = re.compile(r"^[\d+\-\s()#*]+$")
DTMF_REGEX = re.compile(r"^[\d*#\s]+$")
SCHEDULE_TYPES = {"once", "daily", "weekly", "monthly"}


def validate_phone(v: str) -> str:
    if not v or len(v.strip()) == 0:
        raise ValueError("Le numéro ne peut pas être vide")
    if not PHONE_REGEX.match(v.strip()):
        raise ValueError("Format de numéro invalide")
    return v.strip()


def validate_trunk(v: str) -> str:
    if not v or len(v.strip()) == 0:
        raise ValueError("Le trunk ne peut pas être vide")
    return v.strip()


def validate_name_field(v: str, label: str) -> str:
    if not v or len(v.strip()) == 0:
        raise ValueError(f"{label} ne peut pas être vide")
    if len(v.strip()) > 255:
        raise ValueError(f"{label} ne peut pas dépasser 255 caractères")
    return v.strip()


def validate_call_time_value(v: int) -> int:
    if v < 1 or v > 3600:
        raise ValueError("La durée doit être entre 1 et 3600 secondes")
    return v


def validate_dtmf_value(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    if len(v) == 0:
        return None
    if not DTMF_REGEX.match(v):
        raise ValueError("La séquence DTMF ne peut contenir que des chiffres, *, # et espaces")
    return v


def validate_schedule_type_value(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if v not in SCHEDULE_TYPES:
        raise ValueError("Type de planification invalide")
    return v


def validate_schedule_time_value(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if not re.match(r"^\d{2}:\d{2}$", v):
        raise ValueError("L'heure de planification doit etre au format HH:MM")
    hour, minute = [int(part) for part in v.split(":")]
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Heure de planification invalide")
    return v


# ============================================================
# MODELES PYDANTIC
# ============================================================

class CallRequest(BaseModel):
    caller: str
    callee: str
    trunk: str
    call_time_s: int = 30
    dtmf: Optional[str] = None
    time_s_before_dtmf: Optional[int] = None
    time_ms_between_dtmf: Optional[int] = 3000

    @validator("caller", "callee")
    def validate_phone_number(cls, v):
        return validate_phone(v)

    @validator("trunk")
    def validate_trunk_value(cls, v):
        return validate_trunk(v)

    @validator("call_time_s")
    def validate_call_time(cls, v):
        return validate_call_time_value(v)

    @validator("dtmf")
    def validate_dtmf_sequence(cls, v):
        return validate_dtmf_value(v)

    @validator("time_s_before_dtmf")
    def validate_dtmf_delay(cls, v, values):
        if v is not None:
            if v < 0:
                raise ValueError("Le délai DTMF ne peut pas être négatif")
            if "call_time_s" in values and v >= values["call_time_s"]:
                raise ValueError("Le délai DTMF doit être inférieur à la durée totale")
        return v


class ScenarioBase(BaseModel):
    name: str
    keyword: str
    category: str
    caller: str
    callee: str
    trunk: str
    call_time_s: int = 30
    dtmf: Optional[str] = None
    time_s_before_dtmf: Optional[int] = None
    time_ms_between_dtmf: Optional[int] = 3000
    frequency: Optional[str] = None
    schedule_enabled: bool = False
    schedule_type: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_day_of_week: Optional[str] = None
    schedule_date: Optional[str] = None
    schedule_timezone: Optional[str] = None
    prevent_overlap: bool = True
    retry_enabled: bool = False
    active: bool = True

    @validator("caller", "callee")
    def validate_phone_number(cls, v):
        return validate_phone(v)

    @validator("trunk")
    def validate_trunk_value(cls, v):
        return validate_trunk(v)

    @validator("name")
    def validate_name(cls, v):
        return validate_name_field(v, "Le nom")

    @validator("keyword")
    def validate_keyword(cls, v):
        return validate_name_field(v, "Le mot-clé")

    @validator("category")
    def validate_category(cls, v):
        return validate_name_field(v, "La catégorie")

    @validator("call_time_s")
    def validate_call_time(cls, v):
        return validate_call_time_value(v)

    @validator("dtmf")
    def validate_dtmf_sequence(cls, v):
        return validate_dtmf_value(v)

    @validator("time_s_before_dtmf")
    def validate_dtmf_delay(cls, v, values):
        if v is not None:
            if v < 0:
                raise ValueError("Le délai DTMF ne peut pas être négatif")
            if "call_time_s" in values and v >= values["call_time_s"]:
                raise ValueError("Le délai DTMF doit être inférieur à la durée totale")
        return v


    @validator("schedule_type")
    def validate_schedule_type(cls, v):
        return validate_schedule_type_value(v)

    @validator("schedule_time")
    def validate_schedule_time(cls, v):
        return validate_schedule_time_value(v)


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(ScenarioBase):
    pass


class ScenarioPatch(BaseModel):
    name: Optional[str] = None
    keyword: Optional[str] = None
    category: Optional[str] = None
    caller: Optional[str] = None
    callee: Optional[str] = None
    trunk: Optional[str] = None
    call_time_s: Optional[int] = None
    dtmf: Optional[str] = None
    time_s_before_dtmf: Optional[int] = None
    time_ms_between_dtmf: Optional[int] = None
    frequency: Optional[str] = None
    schedule_enabled: Optional[bool] = None
    schedule_type: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_day_of_week: Optional[str] = None
    schedule_date: Optional[str] = None
    schedule_timezone: Optional[str] = None
    prevent_overlap: Optional[bool] = None
    retry_enabled: Optional[bool] = None
    active: Optional[bool] = None

    @validator("caller", "callee")
    def validate_phone_number(cls, v):
        if v is None:
            return v
        return validate_phone(v)

    @validator("trunk")
    def validate_trunk_value(cls, v):
        if v is None:
            return v
        return validate_trunk(v)

    @validator("name")
    def validate_name(cls, v):
        if v is None:
            return v
        return validate_name_field(v, "Le nom")

    @validator("keyword")
    def validate_keyword(cls, v):
        if v is None:
            return v
        return validate_name_field(v, "Le mot-clé")

    @validator("category")
    def validate_category(cls, v):
        if v is None:
            return v
        return validate_name_field(v, "La catégorie")

    @validator("call_time_s")
    def validate_call_time(cls, v):
        if v is None:
            return v
        return validate_call_time_value(v)

    @validator("dtmf")
    def validate_dtmf_sequence(cls, v):
        return validate_dtmf_value(v)

    @validator("schedule_type")
    def validate_schedule_type(cls, v):
        return validate_schedule_type_value(v)

    @validator("schedule_time")
    def validate_schedule_time(cls, v):
        return validate_schedule_time_value(v)


class ScenarioOut(ScenarioBase):
    id: int
    created_at: Optional[str]

    class Config:
        orm_mode = True
