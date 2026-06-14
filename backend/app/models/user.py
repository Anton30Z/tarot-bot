from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(16))
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    readings = relationship("Reading", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    free_usage = relationship("FreeUsage", back_populates="user")
