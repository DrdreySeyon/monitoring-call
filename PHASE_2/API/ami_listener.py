import asyncio
import contextlib
import inspect
import logging
from typing import Optional

from sqlalchemy import text

from config import settings
from database import SessionLocal, create_tables

logger = logging.getLogger(__name__)

_ami_task: Optional[asyncio.Task] = None
_ami_stop_event: Optional[asyncio.Event] = None
_ami_manager = None


def normalize_tech_cause(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def parse_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def update_call_from_hangup(
    uniqueid: str,
    cause,
    cause_txt: Optional[str],
    tech_cause: Optional[str],
    linkedid: Optional[str] = None,
) -> int:
    if not uniqueid:
        return 0

    cause_int = parse_int(cause)
    status = "success" if cause_int == 16 else "failed"

    with SessionLocal() as db:
        result = db.execute(
            text(
                "UPDATE calls "
                "SET hangup_cause = :cause, "
                "hangup_cause_detail = :cause_txt, "
                "sip_error_code = :tech_cause, "
                "status = :status "
                "WHERE channel_id = :uniqueid OR channel_id = :linkedid"
            ),
            {
                "cause": cause_int,
                "cause_txt": cause_txt,
                "tech_cause": normalize_tech_cause(tech_cause),
                "status": status,
                "uniqueid": uniqueid,
                "linkedid": linkedid,
            },
        )
        db.commit()
        return int(result.rowcount or 0)


async def close_manager(manager) -> None:
    for method_name in ("logoff", "disconnect", "close"):
        method = getattr(manager, method_name, None)
        if not method:
            continue
        try:
            result = method()
            if inspect.isawaitable(result):
                await result
            return
        except Exception as exc:
            logger.debug("Erreur fermeture AMI via %s: %s", method_name, exc)


async def run_listener(stop_event: Optional[asyncio.Event] = None) -> None:
    global _ami_manager

    if not settings.ami_enabled:
        logger.warning("AMI listener non demarre: AMI_ENABLED=false")
        return

    try:
        from panoramisk import Manager
    except ImportError as exc:
        raise RuntimeError("Le package panoramisk est requis pour le listener AMI") from exc

    create_tables()

    manager = Manager(
        host=settings.ami_host,
        port=settings.ami_port,
        username=settings.ami_user,
        secret=settings.ami_password,
    )
    _ami_manager = manager

    @manager.register_event("Hangup")
    async def handle_hangup(manager, event):
        uniqueid = event.get("Uniqueid")
        cause = event.get("Cause")
        cause_txt = event.get("Cause-txt")
        tech_cause = event.get("TechCause")
        linkedid = event.get("Linkedid")

        updated = update_call_from_hangup(uniqueid, cause, cause_txt, tech_cause, linkedid)

        logger.info(
            "AMI Hangup uniqueid=%s linkedid=%s cause=%s cause_txt=%s tech_cause=%s updated=%s",
            uniqueid,
            linkedid,
            cause,
            cause_txt,
            tech_cause,
            updated,
        )

    try:
        await manager.connect()
        logger.info("AMI listener demarre sur %s:%s", settings.ami_host, settings.ami_port)

        while True:
            if stop_event:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=3600)
                    break
                except asyncio.TimeoutError:
                    continue
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Arret du listener AMI demande")
        raise
    finally:
        await close_manager(manager)
        if _ami_manager is manager:
            _ami_manager = None
        logger.info("AMI listener arrete")


def is_ami_listener_running() -> bool:
    return bool(_ami_task and not _ami_task.done())


async def start_ami_listener_background() -> bool:
    global _ami_task, _ami_stop_event

    if not settings.ami_enabled:
        logger.info("AMI listener integre desactive: AMI_ENABLED=false")
        return False

    if is_ami_listener_running():
        logger.info("AMI listener deja demarre")
        return True

    _ami_stop_event = asyncio.Event()
    _ami_task = asyncio.create_task(run_listener(_ami_stop_event), name="ami-listener")

    def log_task_result(task: asyncio.Task) -> None:
        with contextlib.suppress(asyncio.CancelledError):
            exc = task.exception()
            if exc:
                logger.error("AMI listener arrete en erreur: %s", exc)

    _ami_task.add_done_callback(log_task_result)
    return True


async def stop_ami_listener_background() -> None:
    global _ami_task, _ami_stop_event

    if not _ami_task:
        return

    if _ami_stop_event:
        _ami_stop_event.set()

    try:
        await asyncio.wait_for(_ami_task, timeout=5)
    except asyncio.TimeoutError:
        _ami_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _ami_task
    finally:
        _ami_task = None
        _ami_stop_event = None


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(run_listener())


if __name__ == "__main__":
    main()
