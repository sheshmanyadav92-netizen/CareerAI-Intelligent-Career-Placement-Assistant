from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings

settings = Settings()

engine_kwargs = {
    "pool_pre_ping": True,
    "future": True,
}
if settings.database_url.startswith("postgresql"):
    engine_kwargs["connect_args"] = {"connect_timeout": 2}

engine = create_engine(settings.database_url, **engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
