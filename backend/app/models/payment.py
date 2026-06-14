import enum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class PaymentProvider(str, enum.Enum):
    telegram = "telegram"
    yookassa = "yookassa"


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    reading_id: Mapped[int | None] = mapped_column(ForeignKey("readings.id", ondelete="SET NULL"), index=True)
    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, native_enum=False, length=32),
        nullable=False,
        default=PaymentProvider.telegram,
        server_default=PaymentProvider.telegram.value,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=32),
        nullable=False,
        default=PaymentStatus.pending,
        server_default=PaymentStatus.pending.value,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="RUB", server_default="RUB")
    external_payment_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    provider_payload_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)

    user = relationship("User", back_populates="payments")
    reading = relationship("Reading", back_populates="payments")
