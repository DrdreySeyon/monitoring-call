import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from config import settings

logger = logging.getLogger(__name__)

engine_options = {"echo": False}

if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update({
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_engine(settings.database_url, **engine_options)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        ensure_schema()
        logger.info("Tables créées avec succès")
    except Exception as exc:
        logger.error(f"Erreur création tables: {exc}")
        raise


def ensure_schema() -> None:
    call_columns = {
        "keyword_expected": "VARCHAR(255) NULL",
        "keyword_detected": "VARCHAR(255) NULL",
        "keyword_status": "VARCHAR(32) NULL",
        "hangup_cause": "INTEGER NULL",
        "hangup_cause_detail": "VARCHAR(255) NULL",
        "sip_error_code": "VARCHAR(64) NULL",
        "vosk_status": "VARCHAR(32) NULL",
        "transcription": "TEXT NULL",
        "recording_path": "VARCHAR(1024) NULL",
        "speech_checked_at": "DATETIME NULL",
        "speech_error": "TEXT NULL",
    }

    scenario_columns = {
        "schedule_enabled": "INTEGER NOT NULL DEFAULT 0",
        "schedule_type": "VARCHAR(32) NULL",
        "schedule_time": "VARCHAR(8) NULL",
        "schedule_day_of_week": "VARCHAR(16) NULL",
        "schedule_date": "VARCHAR(32) NULL",
        "schedule_timezone": "VARCHAR(64) NULL",
        "prevent_overlap": "INTEGER NOT NULL DEFAULT 1",
        "retry_enabled": "INTEGER NOT NULL DEFAULT 0",
        "last_run_at": "DATETIME NULL",
        "last_run_status": "VARCHAR(32) NULL",
        "last_run_error": "TEXT NULL",
        "next_run_at": "DATETIME NULL",
    }

    with engine.begin() as conn:
        dialect = conn.dialect.name

        def existing_columns(table_name: str) -> set[str]:
            if dialect == "sqlite":
                return {
                    row[1]
                    for row in conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
                }

            return {
                row[0]
                for row in conn.execute(text(f"SHOW COLUMNS FROM {table_name}")).fetchall()
            }

        existing_calls = existing_columns("calls")

        for column, definition in call_columns.items():
            if column not in existing_calls:
                conn.execute(text(f"ALTER TABLE calls ADD COLUMN {column} {definition}"))
                logger.info("Colonne calls.%s ajoutee", column)

        existing = existing_columns("scenarios")

        for column, definition in scenario_columns.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE scenarios ADD COLUMN {column} {definition}"))
                logger.info("Colonne scenarios.%s ajoutee", column)


def test_database_connection(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
