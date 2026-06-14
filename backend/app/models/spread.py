from sqlalchemy import Boolean, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Spread(TimestampMixin, Base):
    __tablename__ = "spreads"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="RUB", server_default="RUB")
    cards_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cooldown_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24, server_default="24")
    positions_jsonb: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    readings = relationship("Reading", back_populates="spread")
