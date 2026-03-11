from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Scenario
from ari import perform_call
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_scenarios():
    db: Session = SessionLocal()

    try:
        scenarios = db.query(Scenario).filter(
            Scenario.active == 1
        ).all()

        for s in scenarios:
            try:
                # Tâche quotidienne
                if s.frequency == "daily":
                    perform_call(
                        db=db,
                        caller=s.caller,
                        callee=s.callee,
                        trunk=s.trunk,
                        call_time_s=s.call_time_s,
                        dtmf=s.dtmf,
                        time_s_before_dtmf=s.time_s_before_dtmf,
                        time_ms_between_dtmf=s.time_ms_between_dtmf
                    )
                # Tâche hebdomadaire
                elif s.frequency == "weekly":
                    perform_call(
                        db=db,
                        caller=s.caller,
                        callee=s.callee,
                        trunk=s.trunk,
                        call_time_s=s.call_time_s,
                        dtmf=s.dtmf,
                        time_s_before_dtmf=s.time_s_before_dtmf,
                        time_ms_between_dtmf=s.time_ms_between_dtmf
                    )

            except Exception as e:
                logger.error(f"Erreur scheduler scénario {s.id}: {e}")

    finally:
        db.close()


def start_scheduler():
    # Scheduler des scénarios quotidiens à 8h00
    scheduler.add_job(
        run_scenarios,
        "cron",  # Utilisation du cron pour spécifier l'heure
        hour=8,  # 8h00
        minute=0,  # Minute 0
        second=0,  # Seconde 0
        id="daily_scenarios",  # Un identifiant pour cette tâche
        replace_existing=True  # Remplace toute tâche existante avec ce même ID
    )

    # Scheduler des scénarios hebdomadaires (par exemple, tous les lundis à 9h00)
    scheduler.add_job(
        run_scenarios,
        "cron",  # Utilisation du cron pour spécifier l'heure
        day_of_week="mon",  # Lundi (peut être changé selon le jour de la semaine)
        hour=9,  # 9h00
        minute=0,  # Minute 0
        second=0,  # Seconde 0
        id="weekly_scenarios",  # Un identifiant pour cette tâche hebdomadaire
        replace_existing=True  # Remplace toute tâche existante avec ce même ID
    )

    scheduler.start()

    logger.info("Scheduler démarré, les scénarios quotidiens se lanceront à 8h00 et les scénarios hebdomadaires tous les lundis à 9h00.")
