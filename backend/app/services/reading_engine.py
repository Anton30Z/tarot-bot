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

    if "меша" in position_name or "риск" in position_name or "блок" in position_name or "вызов" in position_name or "ослаб" in position_name:
        return "challenge"
    if "помог" in position_name or "поддерж" in position_name or "ресурс" in position_name or "усилив" in position_name or "плюс" in position_name:
        return "support"
    if "суть" in position_name or "главн" in position_name or "ответ" in position_name:
        return "core"
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
            f"Как возможное развитие карта {card.name_ru} указывает на тему: {meaning}. "
            "Это не жесткий финал, а направление, которое усилится, если текущая линия поведения сохранится."
        )
    if role == "past":
        return (
            f"В прошлом {card.name_ru} оставляет след: {meaning}. "
            "Этот опыт уже влияет на выбор, даже если сейчас кажется второстепенным."
        )
    if role == "self":
        return f"В вашей позиции карта {card.name_ru} раскрывает тему: {meaning}. Это показывает, с каким внутренним состоянием вы входите в ситуацию."
    if role == "other":
        return f"В позиции другой стороны карта {card.name_ru} показывает тему: {meaning}. Здесь важно наблюдать за действиями, а не додумывать за человека."

    return f"В позиции «{position_label}» {card.name_ru} раскрывает тему: {meaning}."


def _opening_text(spread: Spread, score: int, tags: list[str]) -> str:
    motifs = ", ".join(tags[:3]) if tags else "ясность, внимание и спокойный выбор"

    if spread.code == "quick_answer":
        return (
            f"Это короткий расклад на быстрый взгляд: где находится суть вопроса, что может поддержать и какой шаг выглядит разумным. "
            f"Общий фон сейчас: {_score_label(score).lower()}. Главные мотивы: {motifs}."
        )
    if spread.code == "yes_no":
        return (
            f"Этот расклад не дает жесткого приговора, а показывает склонность ответа и условия, которые на него влияют. "
            f"Фон ответа: {_score_label(score).lower()}. Ключевые мотивы: {motifs}."
        )
    if spread.code == "two_options":
        return (
            f"Расклад сравнивает два направления не как «хорошее» и «плохое», а как две разные цены выбора. "
            f"Общий фон: {_score_label(score).lower()}. Главные мотивы: {motifs}."
        )
    if spread.category == "relationships":
        return (
            f"Расклад про отношения показывает не чужие гарантированные мысли, а динамику связи и эмоциональные акценты. "
            f"Общий фон: {_score_label(score).lower()}. Важные мотивы: {motifs}."
        )

    return (
        f"Расклад «{spread.name}» показывает {_score_label(score).lower()}. "
        f"Главные мотивы сейчас: {motifs}. Карты стоит читать как карту состояния, а не как обещание неизбежного результата."
    )


def _card_line(card_snapshot: dict[str, Any]) -> str:
    return f"{card_snapshot['card']['name_ru']} — {card_snapshot['interpretation']['short_meaning']}"


def _synthesis_quick_answer(cards_snapshot: list[dict[str, Any]], score: int) -> str:
    if len(cards_snapshot) < 3:
        return _synthesis_generic(cards_snapshot, score)

    core, support, advice = cards_snapshot[:3]
    if support["card"]["score"] < 0:
        support_bridge = (
            "Поддержка здесь выглядит не как легкий ресурс, а как честное обнаружение слабого места: "
            "если его признать, ситуация становится управляемее."
        )
    else:
        support_bridge = "Поддержка уже есть рядом: ее не нужно изобретать, важно просто начать ею пользоваться."

    return (
        f"Суть вопроса задает {_card_line(core)}. "
        f"То есть главный узел сейчас не во всем сразу, а именно в этой теме. "
        f"Вторая карта, {_card_line(support)}, показывает, за счет чего можно не застрять. {support_bridge} "
        f"Совет через карту {_card_line(advice)} переводит расклад в действие: меньше распыляться и выбрать шаг, который прямо связан с этой картой."
    )


def _yes_no_direction(score: int, first_score: int) -> str:
    total = score + first_score
    if total >= 4:
        return "скорее да, если действовать спокойно и последовательно"
    if total <= -4:
        return "скорее нет или пока не время давить на ситуацию"
    return "смешанный: многое зависит от условий и следующего шага"


def _synthesis_yes_no(cards_snapshot: list[dict[str, Any]], score: int) -> str:
    if len(cards_snapshot) < 3:
        return _synthesis_generic(cards_snapshot, score)

    answer, strengthens, weakens = cards_snapshot[:3]
    direction = _yes_no_direction(score, answer["card"]["score"])
    return (
        f"Главная карта ответа — {_card_line(answer)}. Поэтому общий наклон ответа: {direction}. "
        f"Усиливает ситуацию {_card_line(strengthens)}: это то, на что можно опереться. "
        f"Ослабляет или запутывает ответ {_card_line(weakens)}: эту тему лучше не игнорировать. "
        "Если убрать давление и посмотреть на факты, ответ станет яснее."
    )


def _synthesis_two_options(cards_snapshot: list[dict[str, Any]], score: int) -> str:
    if len(cards_snapshot) < 6:
        return _synthesis_generic(cards_snapshot, score)

    a_plus, a_risk, a_outcome, b_plus, b_risk, b_outcome = cards_snapshot[:6]
    score_a = sum(item["card"]["score"] for item in [a_plus, a_risk, a_outcome])
    score_b = sum(item["card"]["score"] for item in [b_plus, b_risk, b_outcome])
    if score_a > score_b:
        lean = "Вариант A выглядит мягче по общему фону, но его риск все равно нужно учитывать."
    elif score_b > score_a:
        lean = "Вариант B выглядит мягче по общему фону, но он тоже требует честного взгляда на риск."
    else:
        lean = "Оба варианта примерно равны по напряжению; выбор зависит не от выгоды, а от того, какую цену вы готовы принять."

    return (
        f"Вариант A держится на {_card_line(a_plus)}, но его слабое место — {_card_line(a_risk)}. "
        f"Если идти туда, итоговая линия описывается картой {_card_line(a_outcome)}. "
        f"Вариант B дает ресурс через {_card_line(b_plus)}, а напряжение показывает {_card_line(b_risk)}. "
        f"Его итоговая линия — {_card_line(b_outcome)}. {lean}"
    )


def _synthesis_relationship(cards_snapshot: list[dict[str, Any]], score: int) -> str:
    if len(cards_snapshot) < 3:
        return _synthesis_generic(cards_snapshot, score)

    first = cards_snapshot[0]
    middle = cards_snapshot[len(cards_snapshot) // 2]
    last = cards_snapshot[-1]
    if score >= 3:
        tone = "В связи есть ресурс для движения навстречу, но его важно проявлять делом, а не ожиданием."
    elif score <= -3:
        tone = "Связь сейчас требует бережности: резкие выводы могут усилить дистанцию."
    else:
        tone = "Динамика неоднозначная: рядом стоят и интерес, и сомнение."

    return (
        f"Первый акцент расклада — {_card_line(first)}: он задает эмоциональный фон ситуации. "
        f"Средняя точка, карта {_card_line(middle)}, показывает, где находится главный поворот или скрытое напряжение. "
        f"Финальный акцент — {_card_line(last)} — показывает, во что эта динамика может перейти при текущем поведении. {tone}"
    )


def _synthesis_big(cards_snapshot: list[dict[str, Any]], score: int) -> str:
    if len(cards_snapshot) < 5:
        return _synthesis_generic(cards_snapshot, score)

    first = cards_snapshot[0]
    strongest = max(cards_snapshot, key=lambda item: item["card"]["score"])
    hardest = min(cards_snapshot, key=lambda item: item["card"]["score"])
    last = cards_snapshot[-1]

    return (
        f"Большой расклад начинается с темы {_card_line(first)}, поэтому ее стоит считать входом во всю картину. "
        f"Самый поддерживающий ресурс здесь — {_card_line(strongest)}. "
        f"Самое чувствительное место — {_card_line(hardest)}; именно там не стоит торопиться или действовать на автомате. "
        f"Финальный акцент {_card_line(last)} показывает направление, в которое складывается история, если ничего резко не ломать."
    )


def _synthesis_generic(cards_snapshot: list[dict[str, Any]], score: int) -> str:
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


def _synthesis_text(spread: Spread, cards_snapshot: list[dict[str, Any]], score: int) -> str:
    if spread.code == "quick_answer":
        return _synthesis_quick_answer(cards_snapshot, score)
    if spread.code == "yes_no":
        return _synthesis_yes_no(cards_snapshot, score)
    if spread.code == "two_options":
        return _synthesis_two_options(cards_snapshot, score)
    if spread.category == "relationships":
        return _synthesis_relationship(cards_snapshot, score)
    if spread.category == "big":
        return _synthesis_big(cards_snapshot, score)
    return _synthesis_generic(cards_snapshot, score)


def _practical_advice(spread: Spread, cards_snapshot: list[dict[str, Any]], score: int) -> str:
    advice_card = cards_snapshot[-1] if cards_snapshot else None
    if advice_card is None:
        return "Сделайте паузу и вернитесь к вопросу позже."

    if spread.code == "yes_no" and len(cards_snapshot) >= 3:
        answer, strengthens, weakens = cards_snapshot[:3]
        return (
            f"Практически: сначала проверьте тему карты {weakens['card']['name_ru']} — "
            f"«{weakens['interpretation']['short_meaning']}», потому что она может искажать ответ. "
            f"Затем опирайтесь на карту {strengthens['card']['name_ru']}: «{strengthens['interpretation']['short_meaning']}». "
            "После этого вопрос станет честнее, а решение спокойнее."
        )

    if spread.code == "two_options" and len(cards_snapshot) >= 6:
        a_plus, a_risk, a_outcome, b_plus, b_risk, b_outcome = cards_snapshot[:6]
        score_a = sum(item["card"]["score"] for item in [a_plus, a_risk, a_outcome])
        score_b = sum(item["card"]["score"] for item in [b_plus, b_risk, b_outcome])
        chosen = "A" if score_a >= score_b else "B"
        risk = a_risk if chosen == "A" else b_risk
        outcome = a_outcome if chosen == "A" else b_outcome
        return (
            f"Практически: если склоняетесь к варианту {chosen}, не смотрите только на обещанный результат "
            f"({outcome['card']['name_ru']} — {outcome['interpretation']['short_meaning']}). "
            f"Сначала честно проверьте риск: {risk['card']['name_ru']} — {risk['interpretation']['short_meaning']}."
        )

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
    practical_advice = _practical_advice(spread, cards_snapshot, score)

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
