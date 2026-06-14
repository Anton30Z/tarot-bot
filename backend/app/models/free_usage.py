from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FreeUsage(TimestampMixin, Base):
    __tablename__ = "free_usage"
    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_free_usage_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    reading_id: Mapped[int] = mapped_column(ForeignKey("readings.id", ondelete="CASCADE"), index=True, nullable=False)

    user = relationship("User", back_populates="free_usage")
    reading = relationship("Reading", back_populates="free_usage")
