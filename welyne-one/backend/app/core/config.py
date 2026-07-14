"""
Configuration centrale (Pydantic Settings).
Toutes les valeurs viennent du .env — jamais de secret en dur dans le code.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # LLM
    CEREBRAS_API_KEY: str = ""
    MODEL_CEREBRAS: str = "llama-3.3-70b"
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    MODEL_JUDGE: str = "llama-3.3-70b-versatile"
    MODEL_EXTRACT: str = "llama-3.1-8b-instant"
    MODEL_CHAT: str = "llama-3.3-70b-versatile"

    # DB
    DATABASE_URL: str = "postgresql+psycopg://welyne:welyne@localhost:5432/welyne_one"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://welyne:welyne@localhost:5432/welyne_one"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Langfuse
    LANGFUSE_HOST: str = "http://localhost:3001"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""

    # Auth
    JWT_SECRET: str = "change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # PII
    PII_MASK_SALT: str = "change-me-too"

    # Portail candidat (frontend Next.js) — utilisé pour construire les liens
    # réels envoyés au candidat (prescreen_link, booking_link, ...). Doit
    # pointer vers l'URL publique du frontend (ex. http://localhost:3000 en
    # dev, ou l'URL de prod). Ne JAMAIS utiliser le domaine placeholder
    # welyne.example — il n'existe pas et ne résoudra jamais.
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    # Messagerie (phases suivantes)
    SMTP_HOST: str = ""
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_ID: str = ""
    # Token arbitraire choisi par nous, déclaré dans le dashboard Meta pour
    # la vérification du webhook (challenge GET, §6-A5 canal WhatsApp).
    WHATSAPP_VERIFY_TOKEN: str = "change-me-webhook-verify"
    CALCOM_URL: str = ""
    CALCOM_API_KEY: str = ""

    # Boîte mail dédiée aux réponses candidats en pré-qualification (A5,
    # canal "email"). Distincte de la boîte de réception CV (A3) si besoin ;
    # peut pointer vers la même adresse en dev. IMAP4 avec SSL implicite
    # (port 993) par défaut — comme Gmail/Outlook.
    IMAP_HOST: str = ""
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASS: str = ""
    IMAP_MAILBOX: str = "INBOX"
    IMAP_USE_SSL: bool = True
    # Intervalle (secondes) entre deux relevés de boîte, utilisé par le
    # scheduler Celery beat (voir celery_app.py).
    PRESCREEN_EMAIL_POLL_SECONDS: int = 120



@lru_cache
def get_settings() -> Settings:
    return Settings()
