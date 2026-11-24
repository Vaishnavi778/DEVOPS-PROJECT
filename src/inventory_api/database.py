import os
from collections.abc import Generator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker


def database_url() -> str | URL:
    if url := os.getenv("DATABASE_URL"):
        return url

    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER", "inventory"),
        password=os.getenv("DB_PASSWORD", "inventory"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "inventory"),
    )


def create_session_factory(url: str | URL | None = None) -> sessionmaker[Session]:
    engine = create_engine(url or database_url(), pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


SessionLocal = create_session_factory()


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
