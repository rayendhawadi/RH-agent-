"""Table llm_usage — journalisation des tokens par appel LLM (§6-A9 : "tokens & coût estimé par embauche")."""
import uuid
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped


class LLMUsage(Base, UUIDPk, Timestamped):
    __tablename__ = "llm_usage"

    task: Mapped[str] = mapped_column(String(30))          # extract|judge|chat
    trace_name: Mapped[str] = mapped_column(String(80))    # ex: "a4/score@v1"
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(80))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)