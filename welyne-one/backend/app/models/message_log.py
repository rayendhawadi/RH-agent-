"""Table message_log — chaque message sortant (§5.2, A7). Append-only, jamais édité."""
import uuid
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._base import UUIDPk, Timestamped


class MessageLog(Base, UUIDPk, Timestamped):
    __tablename__ = "message_log"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False
    )
    to: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="email")  # email|whatsapp
    template_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rendered_body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent|failed|skipped_rate_limit
    validated_by: Mapped[str] = mapped_column(String(255), default="system")