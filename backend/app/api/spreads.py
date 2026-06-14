from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Spread


router = APIRouter(prefix="/api/spreads", tags=["spreads"])


class SpreadResponse(BaseModel):
    code: str
    name: str
    category: str
    description: str | None
    price: int
    currency: str
    cards_count: int
    cooldown_hours: int
    positions_jsonb: list[dict]
    is_active: bool


@router.get("", response_model=list[SpreadResponse])
async def list_spreads() -> list[SpreadResponse]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Spread)
            .where(Spread.is_active.is_(True))
            .order_by(Spread.category, Spread.price, Spread.name)
        )
        spreads = result.scalars().all()

    return [SpreadResponse.model_validate(spread, from_attributes=True) for spread in spreads]
