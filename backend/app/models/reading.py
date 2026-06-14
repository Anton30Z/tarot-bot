import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ReadingStatus(str, enum.Enum):
    created = "created"
    selecting = "selecting"
    revealed = "revealed"
    expired = "expired"
    cancelled = "cancelled"


class Reading(TimestampMixin, Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    spread_id: Mapped[int] = mapped_column(ForeignKey("spreads.id", ondelete="RESTRICT"), index=True, nullable=False)
    status: Mapped[ReadingStatus] = mapped_column(
        Enum(ReadingStatus, native_enum=False, length=32),
        nullable=False,
        default=ReadingStatus.created,
        server_default=ReadingStatus.created.value,
    )
    cards_jsonb: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    positions_jsonb: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    selected_slots_jsonb: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    revealed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tags_jsonb: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    result_snapshot_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    share_image_url: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    user = relationship("User", back_populates="readings")
    spread = relationship("Spread", back_populates="readings")
    payments = relationship("Payment", back_populates="reading")
    free_usage = relationship("FreeUsage", back_populates="reading")
