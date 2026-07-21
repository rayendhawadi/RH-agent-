"""
Session SQLAlchemy synchrone (utilisée par l'API et les workers Celery).
Postgres 16 + pgvector. Pas de docker requis : pointez DATABASE_URL_SYNC
vers un Postgres local (voir README « Installation sans Docker »).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL_SYNC,
    pool_pre_ping=True,
    pool_recycle=280,  # évite de réutiliser une connexion morte si le
                        # fournisseur cloud (Neon/Supabase, etc.) a coupé la
                        # connexion pendant une mise en veille pour inactivité
    pool_timeout=240,   # Augmenté à 4 minutes pour supporter les connexions lentes
                        # (évite les erreurs de timeout prématurées quand le pool 
                        # ou la connexion réseau est saturé)
    connect_args={"connect_timeout": 240}, # Augmenté à 4 minutes (240s) pour
                        # pallier aux connexions internet (wifi) très lentes,
                        # évitant les erreurs de connexion à Postgres trop rapides.
    future=True,
)
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
