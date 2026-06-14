from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import CardInterpretation


router = APIRouter(prefix="/api/card-interpretations", tags=["card-interpretations"])


class CardInterpretationResponse(BaseModel):
    deck_code: str
    card_code: str
    interpretation_set_code: str
    short_meaning: str
    general: str
    love: str
    career: str
    money: str
    advice: str
    tags_jsonb: list[str]
    score: int


@router.get("", response_model=list[CardInterpretationResponse])
async def list_card_interpretations(
    deck_code: str = "rider_waite_v1",
    interpretation_set_code: str = "commercial_v1",
) -> list[CardInterpretationResponse]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CardInterpretation)
            .where(
                CardInterpretation.deck_code == deck_code,
                CardInterpretation.interpretation_set_code == interpretation_set_code,
            )
            .order_by(CardInterpretation.id)
        )
        interpretations = result.scalars().all()

    return [
        CardInterpretationResponse.model_validate(interpretation, from_attributes=True)
        for interpretation in interpretations
    ]
