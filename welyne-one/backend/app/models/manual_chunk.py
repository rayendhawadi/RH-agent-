from sqlalchemy import Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._base import UUIDPk


class ManualChunk(Base, UUIDPk):
    __tablename__ = "manual_chunks"

    content: Mapped[str] = mapped_column(Text)
    page: Mapped[int] = mapped_column(Integer, nullable=True)
