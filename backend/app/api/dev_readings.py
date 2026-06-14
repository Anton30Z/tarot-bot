from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Reading, ReadingStatus, User
from app.services.reading_engine import (
    ReadingEngineError,
    SpreadNotFoundError,
    create_or_get_reading,
)


router = APIRouter(prefix="/api/dev/readings", tags=["dev-readings"])


class ReadingResponse(BaseModel):
    id: int
    user_id: int
    spread_id: int
    status: str
    cards_jsonb: list[dict[str, Any]]
    positions_jsonb: list[dict[str, Any]]
    selected_slots_jsonb: list[int]
    revealed_count: int
    tags_jsonb: list[str]
    score: int
    result_snapshot_jsonb: dict[str, Any]
    expires_at: str


class SelectCardRequest(BaseModel):
    slot_index: int


async def get_or_create_dev_user(telegram_id: int) -> User:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=f"dev_{telegram_id}",
                first_name="Dev",
                language_code="ru",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


def serialize_reading(reading: Reading) -> ReadingResponse:
    return ReadingResponse(
        id=reading.id,
        user_id=reading.user_id,
        spread_id=reading.spread_id,
        status=reading.status.value if hasattr(reading.status, "value") else str(reading.status),
        cards_jsonb=reading.cards_jsonb,
        positions_jsonb=reading.positions_jsonb,
        selected_slots_jsonb=reading.selected_slots_jsonb,
        revealed_count=reading.revealed_count,
        tags_jsonb=reading.tags_jsonb,
        score=reading.score,
        result_snapshot_jsonb=reading.result_snapshot_jsonb,
        expires_at=reading.expires_at.isoformat(),
    )


@router.post("/{spread_code}", response_model=ReadingResponse)
async def create_dev_reading(
    spread_code: str,
    telegram_id: int = Query(default=100001),
) -> ReadingResponse:
    user = await get_or_create_dev_user(telegram_id)

    async with AsyncSessionLocal() as session:
        try:
            reading = await create_or_get_reading(session, user.id, spread_code)
            await session.commit()
            await session.refresh(reading)
        except SpreadNotFoundError as exc:
            await session.rollback()
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ReadingEngineError as exc:
            await session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return serialize_reading(reading)


@router.get("/demo/{spread_code}", response_model=ReadingResponse)
async def create_demo_reading(
    spread_code: str,
    telegram_id: int = Query(default=100001),
) -> ReadingResponse:
    return await create_dev_reading(spread_code=spread_code, telegram_id=telegram_id)


@router.get("/{reading_id}", response_model=ReadingResponse)
async def get_dev_reading(reading_id: int) -> ReadingResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Reading).where(Reading.id == reading_id))
        reading = result.scalar_one_or_none()
        if reading is None:
            raise HTTPException(status_code=404, detail="Reading not found")
        return serialize_reading(reading)


@router.get("/{reading_id}/plain")
async def get_dev_reading_plain(reading_id: int) -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Reading).where(Reading.id == reading_id))
        reading = result.scalar_one_or_none()
        if reading is None:
            raise HTTPException(status_code=404, detail="Reading not found")

        snapshot = reading.result_snapshot_jsonb or {}
        spread = snapshot.get("spread", {})
        summary = snapshot.get("summary", {})
        narrative = snapshot.get("narrative", {})
        pattern = snapshot.get("pattern", {})
        cards = snapshot.get("cards", [])

        return {
            "id": reading.id,
            "status": reading.status.value if hasattr(reading.status, "value") else str(reading.status),
            "spread": spread.get("name"),
            "description": spread.get("description"),
            "score_label": snapshot.get("score_label"),
            "pattern": pattern,
            "opening": narrative.get("opening") or summary.get("text"),
            "cards": [
                {
                    "position": item.get("position", {}).get("name"),
                    "card": item.get("card", {}).get("name_ru"),
                    "short_meaning": item.get("interpretation", {}).get("short_meaning"),
                    "text": item.get("interpretation", {}).get("text"),
                }
                for item in cards
            ],
            "synthesis": narrative.get("synthesis"),
            "practical_advice": narrative.get("practical_advice") or summary.get("advice"),
        }


@router.get("/{reading_id}/text", response_class=PlainTextResponse)
async def get_dev_reading_text(reading_id: int) -> str:
    plain = await get_dev_reading_plain(reading_id)

    lines: list[str] = [
        f"Расклад: {plain['spread']}",
        "",
        plain["description"] or "",
        "",
        f"Общий фон: {plain['score_label']}",
        "",
        "Вступление",
        plain["opening"] or "",
        "",
        "Карты",
    ]

    for index, card in enumerate(plain["cards"], start=1):
        lines.extend(
            [
                "",
                f"{index}. {card['position']} — {card['card']}",
                card["text"] or "",
            ]
        )

    lines.extend(
        [
            "",
            "Общий смысл расклада",
            plain["synthesis"] or "",
            "",
            "Практический совет",
            plain["practical_advice"] or "",
        ]
    )

    return "\n".join(line for line in lines if line is not None)


@router.post("/{reading_id}/select-card")
async def select_dev_card(reading_id: int, payload: SelectCardRequest) -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Reading).where(Reading.id == reading_id))
        reading = result.scalar_one_or_none()
        if reading is None:
            raise HTTPException(status_code=404, detail="Reading not found")

        selected_slots = list(reading.selected_slots_jsonb or [])
        if payload.slot_index in selected_slots:
            raise HTTPException(status_code=400, detail="Slot already selected")
        if reading.revealed_count >= len(reading.cards_jsonb):
            raise HTTPException(status_code=400, detail="All cards are already revealed")

        reveal_index = reading.revealed_count
        revealed_card = reading.cards_jsonb[reveal_index]
        selected_slots.append(payload.slot_index)

        reading.selected_slots_jsonb = selected_slots
        reading.revealed_count = reveal_index + 1
        reading.status = (
            ReadingStatus.revealed
            if reading.revealed_count >= len(reading.cards_jsonb)
            else ReadingStatus.selecting
        )
        await session.commit()
        await session.refresh(reading)

        return {
            "reading_id": reading.id,
            "slot_index": payload.slot_index,
            "reveal_index": reveal_index + 1,
            "card": revealed_card,
            "status": reading.status.value,
            "revealed_count": reading.revealed_count,
            "selected_slots_jsonb": reading.selected_slots_jsonb,
        }


@router.get("/demo/{reading_id}/select/{slot_index}")
async def select_demo_card(reading_id: int, slot_index: int) -> dict[str, Any]:
    return await select_dev_card(reading_id=reading_id, payload=SelectCardRequest(slot_index=slot_index))
