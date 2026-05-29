from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_is_sqlite = "sqlite" in settings.database_url

_connect_args: dict = {}
_engine_kwargs: dict = {}

if _is_sqlite:
    _connect_args = {"check_same_thread": False}
    _engine_kwargs = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
    }

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=settings.debug,
    **_engine_kwargs,
)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA cache_size=-4000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
