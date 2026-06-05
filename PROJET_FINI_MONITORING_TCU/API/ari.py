import logging
import traceback
from typing import Optional, Dict, List, Tuple

import requests
from requests.auth import HTTPBasicAuth
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from models import Call

logger = logging.getLogger(__name__)


def fetch_cdr_duration(channel_id: str, db: Session) -> Optional[int]:
    """
    Va lire la table CDR d’Asterisk pour récupérer la durée en secondes.
    La requête peut devoir être adaptée selon ta vraie base CDR.
    """
    if not channel_id:
        return None

    try:
        result = db.execute(
            text(
                "SELECT duration FROM cdr "
                "WHERE uniqueid = :uid "
                "ORDER BY calldate DESC "
                "LIMIT 1"
            ),
            {"uid": channel_id}
        ).first()
    except Exception as exc:
        logger.warning(f"Erreur lors de la récupération CDR pour {channel_id}: {exc}")
        return None

    if not result:
        return None

    duration = result[0]
    if duration is None:
        return None

    try:
        return int(duration)
    except Exception:
        return None


def fetch_multiple_cdr_durations(channel_ids: List[str], db: Session) -> dict:
    if not channel_ids:
        return {}

    try:
        rows = db.execute(
            text(
                "SELECT uniqueid, duration FROM cdr "
                "WHERE uniqueid IN :channel_ids "
                "AND duration IS NOT NULL "
                "ORDER BY calldate DESC"
            ),
            {"channel_ids": tuple(channel_ids)}
        ).fetchall()

        return {row[0]: int(row[1]) for row in rows}
    except Exception as exc:
        logger.warning(f"Erreur lors de la récupération CDR multiple: {exc}")
        return {}


def test_ari_connection() -> dict:
    try:
        resp = requests.get(
            f"{settings.ari_url}/asterisk/info",
            auth=HTTPBasicAuth(settings.ari_user, settings.ari_password),
            timeout=5
        )

        if resp.status_code == 200:
            info = resp.json()
            return {
                "status": "ok",
                "message": "ARI connection successful",
                "asterisk_version": info.get("build", {}).get("version", "unknown")
            }

        return {
            "status": "error",
            "message": f"HTTP {resp.status_code}: {resp.text}"
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc)
        }


def build_ari_variables(
    call_time_s: int = 30,
    dtmf: Optional[str] = None,
    time_s_before_dtmf: Optional[int] = None,
    time_ms_between_dtmf: Optional[int] = None
) -> Dict[str, str]:
    variables = {
        "call_time_s": str(call_time_s)
    }

    if dtmf and dtmf.strip():
        variables.update({
            "dtmf": dtmf.strip(),
            "time_s_before_dtmf": str(time_s_before_dtmf if time_s_before_dtmf is not None else 4),
            "time_ms_between_dtmf": str(time_ms_between_dtmf if time_ms_between_dtmf is not None else 3000)
        })

    return variables


def perform_call(
    db: Session,
    caller: str,
    callee: str,
    trunk: str,
    call_time_s: int = 30,
    dtmf: Optional[str] = None,
    time_s_before_dtmf: Optional[int] = None,
    time_ms_between_dtmf: Optional[int] = None,
    scenario_id: Optional[int] = None,
    scenario_name: Optional[str] = None,
    scenario_keyword: Optional[str] = None,
    scenario_category: Optional[str] = None
) -> Tuple[Call, dict]:
    endpoint = f"PJSIP/{callee}@{trunk}"

    variables = build_ari_variables(
        call_time_s=call_time_s,
        dtmf=dtmf,
        time_s_before_dtmf=time_s_before_dtmf,
        time_ms_between_dtmf=time_ms_between_dtmf
    )

    payload = {
        "variables": variables
    }

    params = {
        "endpoint": endpoint,
        "extension": callee,
        "context": "recording",
        "priority": "1",
        "callerId": caller
    }

    call_row = None

    try:
        logger.info(f"Initiation d'appel de {caller} vers {callee} via {trunk}")

        call_row = Call(
            endpoint=endpoint,
            caller=caller,
            callee=callee,
            trunk=trunk,
            status="in_progress",
            call_time_s=call_time_s,
            dtmf=dtmf,
            time_s_before_dtmf=time_s_before_dtmf,
            time_ms_between_dtmf=time_ms_between_dtmf,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            scenario_keyword=scenario_keyword,
            scenario_category=scenario_category,
            keyword_expected=scenario_keyword,
            keyword_status="pending" if scenario_keyword else None
        )
        db.add(call_row)
        db.commit()
        db.refresh(call_row)

        resp = requests.post(
            f"{settings.ari_url}/channels",
            params=params,
            json=payload,
            auth=HTTPBasicAuth(settings.ari_user, settings.ari_password),
            timeout=10
        )

        if resp.status_code not in (200, 201):
            error_msg = f"Erreur ARI HTTP {resp.status_code}: {resp.text}"
            logger.error(error_msg)

            call_row.status = "failed"
            call_row.error_message = error_msg
            db.commit()

            raise HTTPException(status_code=resp.status_code, detail=error_msg)

        ari_response = resp.json()
        channel_id = ari_response.get("id")

        call_row.channel_id = channel_id
        call_row.status = "success"
        db.commit()
        db.refresh(call_row)

        logger.info(f"Appel créé avec succès - ID: {call_row.id}, Channel: {channel_id}")
        return call_row, ari_response

    except requests.RequestException as exc:
        error_msg = f"Erreur de communication avec ARI : {str(exc)}"
        logger.error(error_msg)

        if call_row:
            call_row.status = "failed"
            call_row.error_message = error_msg
            db.commit()

        raise HTTPException(status_code=503, detail=error_msg)

    except HTTPException:
        raise

    except Exception as exc:
        logger.error(f"Erreur inattendue lors de l'appel: {str(exc)}\n{traceback.format_exc()}")

        if call_row:
            call_row.status = "failed"
            call_row.error_message = str(exc)
            db.commit()

        raise HTTPException(status_code=500, detail="Erreur interne lors de l’initiation de l’appel")
