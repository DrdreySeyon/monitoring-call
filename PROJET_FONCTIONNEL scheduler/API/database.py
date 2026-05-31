import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    echo=False
)

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
        existing = {
            row[0]
            for row in conn.execute(text("SHOW COLUMNS FROM scenarios")).fetchall()
        }

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
