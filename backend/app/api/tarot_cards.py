from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import TarotCard


router = APIRouter(prefix="/api/tarot-cards", tags=["tarot-cards"])


class TarotCardResponse(BaseModel):
    deck_code: str
    card_code: str
    name_ru: str
    name_en: str
    arcana: str
    suit: str | None
    image_url: str | None
    score: int
    is_active: bool


@router.get("", response_model=list[TarotCardResponse])
async def list_tarot_cards(deck_code: str = "rider_waite_v1") -> list[TarotCardResponse]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TarotCard)
            .where(TarotCard.deck_code == deck_code, TarotCard.is_active.is_(True))
            .order_by(TarotCard.id)
        )
        cards = result.scalars().all()

    return [TarotCardResponse.model_validate(card, from_attributes=True) for card in cards]
