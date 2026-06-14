"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=False)

    op.create_table(
        "spreads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="RUB", nullable=False),
        sa.Column("cards_count", sa.Integer(), nullable=False),
        sa.Column("cooldown_hours", sa.Integer(), server_default="24", nullable=False),
        sa.Column("positions_jsonb", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_spreads_category"), "spreads", ["category"], unique=False)
    op.create_index(op.f("ix_spreads_code"), "spreads", ["code"], unique=False)

    op.create_table(
        "tarot_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deck_code", sa.String(length=64), nullable=False),
        sa.Column("card_code", sa.String(length=64), nullable=False),
        sa.Column("name_ru", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("arcana", sa.String(length=64), nullable=False),
        sa.Column("suit", sa.String(length=64), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deck_code", "card_code", name="uq_tarot_cards_deck_card"),
    )
    op.create_index(op.f("ix_tarot_cards_card_code"), "tarot_cards", ["card_code"], unique=False)
    op.create_index(op.f("ix_tarot_cards_deck_code"), "tarot_cards", ["deck_code"], unique=False)

    op.create_table(
        "card_interpretations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deck_code", sa.String(length=64), nullable=False),
        sa.Column("card_code", sa.String(length=64), nullable=False),
        sa.Column("interpretation_set_code", sa.String(length=64), server_default="default_v1", nullable=False),
        sa.Column("short_meaning", sa.Text(), nullable=False),
        sa.Column("general", sa.Text(), nullable=False),
        sa.Column("love", sa.Text(), nullable=False),
        sa.Column("career", sa.Text(), nullable=False),
        sa.Column("money", sa.Text(), nullable=False),
        sa.Column("advice", sa.Text(), nullable=False),
        sa.Column("tags_jsonb", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deck_code", "card_code", "interpretation_set_code", name="uq_card_interpretations_deck_card_set"),
    )
    op.create_index(op.f("ix_card_interpretations_card_code"), "card_interpretations", ["card_code"], unique=False)
    op.create_index(op.f("ix_card_interpretations_deck_code"), "card_interpretations", ["deck_code"], unique=False)

    op.create_table(
        "card_combinations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deck_code", sa.String(length=64), nullable=False),
        sa.Column("combination_key", sa.String(length=255), nullable=False),
        sa.Column("card_codes_jsonb", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("topic", sa.String(length=64), server_default="general", nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False),
        sa.Column("tags_jsonb", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("score_delta", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deck_code", "combination_key", "topic", name="uq_card_combinations_deck_key_topic"),
    )
    op.create_index(op.f("ix_card_combinations_deck_code"), "card_combinations", ["deck_code"], unique=False)

    op.create_table(
        "readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("spread_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("created", "selecting", "revealed", "expired", "cancelled", native_enum=False, length=32), server_default="created", nullable=False),
        sa.Column("cards_jsonb", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("positions_jsonb", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("selected_slots_jsonb", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("revealed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tags_jsonb", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("result_snapshot_jsonb", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("share_image_url", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["spread_id"], ["spreads.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_readings_expires_at"), "readings", ["expires_at"], unique=False)
    op.create_index(op.f("ix_readings_spread_id"), "readings", ["spread_id"], unique=False)
    op.create_index(op.f("ix_readings_user_id"), "readings", ["user_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.Enum("telegram", "yookassa", native_enum=False, length=32), server_default="telegram", nullable=False),
        sa.Column("status", sa.Enum("pending", "paid", "failed", "refunded", native_enum=False, length=32), server_default="pending", nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="RUB", nullable=False),
        sa.Column("external_payment_id", sa.String(length=255), nullable=True),
        sa.Column("provider_payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_payment_id"),
    )
    op.create_index(op.f("ix_payments_reading_id"), "payments", ["reading_id"], unique=False)
    op.create_index(op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False)

    op.create_table(
        "free_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "usage_date", name="uq_free_usage_user_date"),
    )
    op.create_index(op.f("ix_free_usage_reading_id"), "free_usage", ["reading_id"], unique=False)
    op.create_index(op.f("ix_free_usage_user_id"), "free_usage", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_free_usage_user_id"), table_name="free_usage")
    op.drop_index(op.f("ix_free_usage_reading_id"), table_name="free_usage")
    op.drop_table("free_usage")
    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_reading_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_readings_user_id"), table_name="readings")
    op.drop_index(op.f("ix_readings_spread_id"), table_name="readings")
    op.drop_index(op.f("ix_readings_expires_at"), table_name="readings")
    op.drop_table("readings")
    op.drop_index(op.f("ix_card_combinations_deck_code"), table_name="card_combinations")
    op.drop_table("card_combinations")
    op.drop_index(op.f("ix_card_interpretations_deck_code"), table_name="card_interpretations")
    op.drop_index(op.f("ix_card_interpretations_card_code"), table_name="card_interpretations")
    op.drop_table("card_interpretations")
    op.drop_index(op.f("ix_tarot_cards_deck_code"), table_name="tarot_cards")
    op.drop_index(op.f("ix_tarot_cards_card_code"), table_name="tarot_cards")
    op.drop_table("tarot_cards")
    op.drop_index(op.f("ix_spreads_code"), table_name="spreads")
    op.drop_index(op.f("ix_spreads_category"), table_name="spreads")
    op.drop_table("spreads")
    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_table("users")
