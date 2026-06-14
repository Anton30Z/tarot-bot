from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TarotCard(TimestampMixin, Base):
    __tablename__ = "tarot_cards"
    __table_args__ = (UniqueConstraint("deck_code", "card_code", name="uq_tarot_cards_deck_card"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    deck_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    card_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    arcana: Mapped[str] = mapped_column(String(64), nullable=False)
    suit: Mapped[str | None] = mapped_column(String(64))
    image_url: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class CardInterpretation(TimestampMixin, Base):
    __tablename__ = "card_interpretations"
    __table_args__ = (
        UniqueConstraint(
            "deck_code",
            "card_code",
            "interpretation_set_code",
            name="uq_card_interpretations_deck_card_set",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    deck_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    card_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    interpretation_set_code: Mapped[str] = mapped_column(String(64), nullable=False, default="default_v1", server_default="default_v1")
    short_meaning: Mapped[str] = mapped_column(Text, nullable=False)
    general: Mapped[str] = mapped_column(Text, nullable=False)
    love: Mapped[str] = mapped_column(Text, nullable=False)
    career: Mapped[str] = mapped_column(Text, nullable=False)
    money: Mapped[str] = mapped_column(Text, nullable=False)
    advice: Mapped[str] = mapped_column(Text, nullable=False)
    tags_jsonb: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class CardCombination(TimestampMixin, Base):
    __tablename__ = "card_combinations"
    __table_args__ = (
        UniqueConstraint(
            "deck_code",
            "combination_key",
            "topic",
            name="uq_card_combinations_deck_key_topic",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    deck_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    combination_key: Mapped[str] = mapped_column(String(255), nullable=False)
    card_codes_jsonb: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    topic: Mapped[str] = mapped_column(String(64), nullable=False, default="general", server_default="general")
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
    tags_jsonb: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    score_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
