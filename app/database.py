from urllib.parse import quote

from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()


def _normalize_database_url(url: str) -> str:
    """Normalize common copied Supabase URL formats to a SQLAlchemy-safe DSN."""
    if not url:
        return url

    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql://" + normalized[len("postgres://") :]

    # Handle URLs copied as: postgresql://user:[p@ss]@host:5432/db
    marker = ":["
    start = normalized.find(marker)
    if start != -1:
        end = normalized.find("]@", start + len(marker))
        if end != -1:
            raw_password = normalized[start + len(marker) : end]
            encoded_password = quote(raw_password, safe="")
            normalized = f"{normalized[: start + 1]}{encoded_password}{normalized[end + 1 :]}"

    return normalized


# During local no-auth testing, force SQLite to keep all routes reachable.
database_url = (
    settings.DATABASE_URL
    if settings.AUTH_BYPASS
    else (_normalize_database_url(settings.SUPABASE_DATABASE_URL) or settings.DATABASE_URL)
)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    global engine
    try:
        SQLModel.metadata.create_all(engine)
    except OperationalError:
        # Supabase may be unreachable in local/dev networks; fallback to SQLite.
        fallback_url = settings.DATABASE_URL
        fallback_connect_args = {"check_same_thread": False} if fallback_url.startswith("sqlite") else {}
        engine = create_engine(fallback_url, echo=False, connect_args=fallback_connect_args)
        SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
