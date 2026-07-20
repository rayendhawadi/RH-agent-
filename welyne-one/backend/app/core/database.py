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
    pool_timeout=10,    # échoue en 10s avec une erreur claire plutôt que de
                        # bloquer 30s (comportement perçu comme "figé" côté
                        # frontend) quand le pool est temporairement saturé
                        # (ex. base cloud en train de se réveiller + clics
                        # répétés empilant des requêtes)
    connect_args={"connect_timeout": 10},  # sans ceci, psycopg peut rester
                        # bloqué plusieurs MINUTES sur une connexion internet
                        # faible avant d'abandonner (observé : ~12 min sur un
                        # worker Celery) — 10s ici fait échouer vite, avec un
                        # message clair, plutôt qu'un blocage silencieux
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
