"""Table prompt_versions — registre §5.3, synchronisé depuis /prompts/<agent>/*.md au démarrage."""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped


class PromptVersion(Base, UUIDPk, Timestamped):
    __tablename__ = "prompt_versions"

    agent: Mapped[str] = mapped_column(String(10))       # a1, a3, a4, ...
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(20))      # v1, v2, ...
    template: Mapped[str] = mapped_column(Text)
