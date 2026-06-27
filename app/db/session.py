from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def init_db() -> None:
    from app.models import job  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_job_columns()
    _ensure_sqlite_scene_columns()


def _ensure_sqlite_job_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "jobs" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("jobs")}
    statements = []
    if "telegram_status" not in existing:
        statements.append("ALTER TABLE jobs ADD COLUMN telegram_status VARCHAR(40)")
    if "telegram_error" not in existing:
        statements.append("ALTER TABLE jobs ADD COLUMN telegram_error TEXT")
    if "telegram_sent_at" not in existing:
        statements.append("ALTER TABLE jobs ADD COLUMN telegram_sent_at DATETIME")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _ensure_sqlite_scene_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "scenes" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("scenes")}
    statements = []
    if "audio_prompt_id" not in existing:
        statements.append("ALTER TABLE scenes ADD COLUMN audio_prompt_id VARCHAR(120)")
    if "audio_error" not in existing:
        statements.append("ALTER TABLE scenes ADD COLUMN audio_error TEXT")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
