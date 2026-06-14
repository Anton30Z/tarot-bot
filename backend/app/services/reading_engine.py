from __future__ import annotations

import random
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CardCombination, CardInterpretation, Reading, ReadingStatus, Spread, TarotCard


INTERPRETATION_SET_CODE = "commercial_v1"
DECK_CODE = "rider_waite_v1"


class ReadingEngineError(Exception):
    pass


class SpreadNotFoundError(ReadingEngineError):
    pass


class TarotContentError(ReadingEngineError):
    pass


def _topic_for_spread(spread: Spread) -> str:
    if spread.category == "relationships":
        return "love"
    if spread.category == "work_money":
        return "career"
    if spread.code == "finances":
        return "money"
    if spread.category == "personal":
        return "advice"
    return "general"


def _interpretation_text(interpretation: CardInterpretation, topic: str) -> str:
    return getattr(interpretation, topic, interpretation.general)


def _score_tone(score: int) -> str:
    if score >= 2:
        return "поддерживающая"
    if score <= -2:
        return "напряженная"
    return "нейтральная"


def _position_role(position: dict[str, Any]) -> str:
    position_name = str(position.get("name") or "").lower()

    if "суть" in position_name or "главн" in position_name or "ответ" in position_name:
        return "core"
    if "помог" in position_name or "поддерж" in position_name or "ресурс" in position_name:
        return "support"
    if "меша" in position_name or "риск" in position_name or "блок" in position_name:
        return "challenge"
    if "совет" in position_name or "шаг" in position_name:
        return "advice"
    if "итог" in position_name or "развит" in position_name or "будущ" in position_name:
        return "outcome"
    if "прошл" in position_name:
        return "past"
    if "ваш" in position_name or "вы" == position_name:
        return "self"
    if "партнер" in position_name:
        return "other"
    return "general"


def _position_text(card: TarotCard, position: dict[str, Any], interpretation: CardInterpretation) -> str:
    position_label = position.get("name", "Карта")
    role = _position_role(position)
    meaning = interpretation.short_meaning
    tone = _score_tone(card.score)

    if role == "core":
        return (
            f"В центре вопроса стоит {card.name_ru}: {meaning}. "
            f"Это {tone} карта, поэтому суть ситуации лучше читать через главный мотив карты, а не через внешние детали."
        )
    if role == "support":
        if card.score < 0:
            return (
                f"Как помощь выпадает {card.name_ru}: {meaning}. "
                "Поддержка здесь не в легкости, а в честном признании слабого места: когда оно названо, им уже проще управлять."
            )
        return (
            f"В позиции поддержки {card.name_ru} дает ресурс: {meaning}. "
            "На это качество можно опереться, чтобы не действовать из спешки или тревоги."
        )
    if role == "challenge":
        if card.score > 0:
            return (
                f"В зоне напряжения {card.name_ru} показывает не угрозу, а чрезмерность: {meaning}. "
                "Даже хороший ресурс может мешать, если давить им на ситуацию слишком сильно."
            )
        return (
            f"В зоне сложности {card.name_ru} говорит о теме: {meaning}. "
            "Это место требует осторожности, ясных границ и отказа от резких выводов."
        )
    if role == "advice":
        return (
            f"Совет дает {card.name_ru}: {meaning}. "
            "Практически это про один небольшой шаг, который возвращает больше ясности, чем долгие размышления."
        )
    if role == "outcome":
        return (
            f"Как возможное развитие {card.name_ru} указывает на {meaning}. "
            "Это не жесткий финал, а направление, которое усилится, если текущая линия поведения сохранится."
        )
    if role == "past":
        return (
            f"В прошлом {card.name_ru} оставляет след: {meaning}. "
            "Этот опыт уже влияет на выбор, даже если сейчас кажется второстепенным."
        )
    if role == "self":
        return f"В вашей позиции {card.name_ru} раскрывает {meaning}. Это показывает, с каким внутренним состоянием вы входите в ситуацию."
    if role == "other":
        return f"В позиции другой стороны {card.name_ru} показывает {meaning}. Здесь важно наблюдать за действиями, а не додумывать за человека."

    return f"В позиции «{position_label}» {card.name_ru} раскрывает тему: {meaning}."


def _opening_text(spread: Spread, score: int, tags: list[str]) -> str:
    motifs = ", ".join(tags[:3]) if tags else "ясность, внимание и спокойный выбор"
    return (
        f"Расклад «{spread.name}» показывает {_score_label(score).lower()}. "
        f"Главные мотивы сейчас: {motifs}. Карты стоит читать как карту состояния, а не как обещание неизбежного результата."
    )


def _synthesis_text(spread: Spread, cards_snapshot: list[dict[str, Any]], score: int) -> str:
    if not cards_snapshot:
        return "Расклад пока не содержит карт для синтеза."

    first = cards_snapshot[0]
    last = cards_snapshot[-1]
    first_card = first["card"]["name_ru"]
    first_meaning = first["interpretation"]["short_meaning"]
    last_card = last["card"]["name_ru"]
    last_meaning = last["interpretation"]["short_meaning"]

    if len(cards_snapshot) == 1:
        return (
            f"Главный смысл расклада сосредоточен в карте {first_card}: {first_meaning}. "
            "Сегодня важнее не искать много вариантов, а услышать один ясный акцент."
        )

    if score >= 3:
        bridge = "Общий рисунок скорее поддерживает движение вперед"
    elif score <= -3:
        bridge = "Общий рисунок просит замедлиться и не давить на ситуацию"
    else:
        bridge = "Общий рисунок неоднозначный: в нем есть и ресурс, и зона сомнения"

    return (
        f"{bridge}. Начальная карта, {first_card}, задает тему «{first_meaning}», "
        f"а финальный акцент карты {last_card} переводит ее в «{last_meaning}». "
        "Между этими точками и находится главный выбор: что усилить, а что перестать кормить вниманием."
    )


def _practical_advice(cards_snapshot: list[dict[str, Any]], score: int) -> str:
    advice_card = cards_snapshot[-1] if cards_snapshot else None
    if advice_card is None:
        return "Сделайте паузу и вернитесь к вопросу позже."

    card_name = advice_card["card"]["name_ru"]
    meaning = advice_card["interpretation"]["short_meaning"]
    if score <= -3:
        return (
            f"Практический шаг по карте {card_name}: снизить давление и разобраться с темой «{meaning}» без резких решений. "
            "Лучше выбрать действие, которое уменьшает тревогу, а не доказывает правоту."
        )
    return (
        f"Практический шаг по карте {card_name}: взять тему «{meaning}» как ориентир для ближайшего действия. "
        "Пусть это будет маленький шаг, после которого ситуация станет понятнее."
    )


def _score_label(score: int) -> str:
    if score >= 8:
        return "Сильный поддерживающий фон"
    if score >= 3:
        return "Спокойно-поддерживающий фон"
    if score > -3:
        return "Смешанный фон, многое зависит от выбора"
    if score > -8:
        return "Напряженный фон, нужен бережный темп"
    return "Сильное напряжение, важно не спешить"


def _unique_tags(interpretations: list[CardInterpretation]) -> list[str]:
    counter: Counter[str] = Counter()
    for interpretation in interpretations:
        counter.update(interpretation.tags_jsonb or [])
    return [tag for tag, _count in counter.most_common(10)]


def _build_cards_snapshot(
    cards: list[TarotCard],
    interpretations_by_code: dict[str, CardInterpretation],
    positions: list[dict[str, Any]],
    topic: str,
) -> list[dict[str, Any]]:
    snapshot: list[dict[str, Any]] = []

    for index, (card, position) in enumerate(zip(cards, positions), start=1):
        interpretation = interpretations_by_code[card.card_code]
        snapshot.append(
            {
                "index": index,
                "position": position,
                "card": {
                    "deck_code": card.deck_code,
                    "card_code": card.card_code,
                    "name_ru": card.name_ru,
                    "name_en": card.name_en,
                    "arcana": card.arcana,
                    "suit": card.suit,
                    "image_url": card.image_url,
                    "score": card.score,
                },
                "interpretation": {
                    "interpretation_set_code": interpretation.interpretation_set_code,
                    "short_meaning": interpretation.short_meaning,
                    "base_text": _interpretation_text(interpretation, topic),
                    "text": _position_text(card, position, interpretation),
                    "advice": interpretation.advice,
                    "tags": interpretation.tags_jsonb,
                    "score": interpretation.score,
                },
            }
        )

    return snapshot


async def _get_active_reading(
    session: AsyncSession,
    user_id: int,
    spread_id: int,
    now: datetime,
) -> Reading | None:
    result = await session.execute(
        select(Reading)
        .where(
            Reading.user_id == user_id,
            Reading.spread_id == spread_id,
            Reading.expires_at > now,
            Reading.status != ReadingStatus.cancelled,
        )
        .order_by(Reading.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_or_get_reading(
    session: AsyncSession,
    user_id: int,
    spread_code: str,
) -> Reading:
    now = datetime.now(UTC)

    spread_result = await session.execute(
        select(Spread).where(Spread.code == spread_code, Spread.is_active.is_(True))
    )
    spread = spread_result.scalar_one_or_none()
    if spread is None:
        raise SpreadNotFoundError(f"Spread '{spread_code}' not found")

    active_reading = await _get_active_reading(session, user_id, spread.id, now)
    if active_reading is not None:
        return active_reading

    cards_result = await session.execute(
        select(TarotCard).where(
            TarotCard.deck_code == DECK_CODE,
            TarotCard.is_active.is_(True),
        )
    )
    available_cards = list(cards_result.scalars().all())
    if len(available_cards) < spread.cards_count:
        raise TarotContentError("Not enough active tarot cards")

    selected_cards = random.sample(available_cards, spread.cards_count)
    card_codes = [card.card_code for card in selected_cards]

    interpretations_result = await session.execute(
        select(CardInterpretation).where(
            CardInterpretation.deck_code == DECK_CODE,
            CardInterpretation.interpretation_set_code == INTERPRETATION_SET_CODE,
            CardInterpretation.card_code.in_(card_codes),
        )
    )
    interpretations = list(interpretations_result.scalars().all())
    interpretations_by_code = {item.card_code: item for item in interpretations}
    if len(interpretations_by_code) != len(card_codes):
        raise TarotContentError("Some selected cards have no interpretation")

    topic = _topic_for_spread(spread)
    positions = spread.positions_jsonb or []
    cards_snapshot = _build_cards_snapshot(selected_cards, interpretations_by_code, positions, topic)
    selected_interpretations = [interpretations_by_code[code] for code in card_codes]
    score = sum(item["card"]["score"] for item in cards_snapshot)
    tags = _unique_tags(selected_interpretations)

    combinations_result = await session.execute(
        select(CardCombination).where(
            CardCombination.deck_code == DECK_CODE,
            CardCombination.is_active.is_(True),
        )
    )
    combinations = [
        {
            "combination_key": item.combination_key,
            "topic": item.topic,
            "meaning": item.meaning,
            "tags": item.tags_jsonb,
            "score_delta": item.score_delta,
        }
        for item in combinations_result.scalars().all()
        if set(item.card_codes_jsonb or []).issubset(set(card_codes))
    ]

    opening = _opening_text(spread, score, tags)
    synthesis = _synthesis_text(spread, cards_snapshot, score)
    practical_advice = _practical_advice(cards_snapshot, score)

    result_snapshot = {
        "version": "reading_engine_v2",
        "created_at": now.isoformat(),
        "deck_code": DECK_CODE,
        "interpretation_set_code": INTERPRETATION_SET_CODE,
        "spread": {
            "code": spread.code,
            "name": spread.name,
            "category": spread.category,
            "description": spread.description,
            "cards_count": spread.cards_count,
            "cooldown_hours": spread.cooldown_hours,
        },
        "topic": topic,
        "cards": cards_snapshot,
        "tags": tags,
        "score": score,
        "score_label": _score_label(score),
        "combinations": combinations,
        "narrative": {
            "opening": opening,
            "synthesis": synthesis,
            "practical_advice": practical_advice,
        },
        "summary": {
            "title": f"{spread.name}: {_score_label(score)}",
            "text": opening,
            "advice": practical_advice,
        },
    }

    reading = Reading(
        user_id=user_id,
        spread_id=spread.id,
        status=ReadingStatus.created,
        cards_jsonb=cards_snapshot,
        positions_jsonb=positions,
        selected_slots_jsonb=[],
        revealed_count=0,
        tags_jsonb=tags,
        score=score,
        result_snapshot_jsonb=result_snapshot,
        expires_at=now + timedelta(hours=spread.cooldown_hours),
    )
    session.add(reading)
    await session.flush()
    await session.refresh(reading)
    return reading
