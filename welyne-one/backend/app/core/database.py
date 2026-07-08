"""
Session SQLAlchemy synchrone (utilisée par l'API et les workers Celery).
Postgres 16 + pgvector. Pas de docker requis : pointez DATABASE_URL_SYNC
vers un Postgres local (voir README « Installation sans Docker »).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dépendance FastAPI : une session par requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
