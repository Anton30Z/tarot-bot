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


def _polarity(score: int) -> str:
    if score >= 2:
        return "plus"
    if score <= -2:
        return "minus"
    return "neutral"


def _analyze_pattern(cards_snapshot: list[dict[str, Any]], score: int) -> dict[str, Any]:
    plus_cards = [item for item in cards_snapshot if _polarity(item["card"]["score"]) == "plus"]
    minus_cards = [item for item in cards_snapshot if _polarity(item["card"]["score"]) == "minus"]
    neutral_cards = [item for item in cards_snapshot if _polarity(item["card"]["score"]) == "neutral"]
    strongest = max(cards_snapshot, key=lambda item: item["card"]["score"], default=None)
    hardest = min(cards_snapshot, key=lambda item: item["card"]["score"], default=None)
    advice_card = cards_snapshot[-1] if cards_snapshot else None

    if len(minus_cards) == 0 and len(plus_cards) >= 2:
        code = "supportive"
        label = "поддерживающий рисунок"
    elif len(plus_cards) >= 1 and advice_card and advice_card["card"]["score"] > 0 and score >= 0:
        code = "mixed_with_exit"
        label = "смешанный рисунок с выходом"
    elif len(minus_cards) > len(plus_cards):
        code = "tense_needs_pause"
        label = "напряженный рисунок, лучше замедлиться"
    elif advice_card and advice_card["card"]["score"] < 0:
        code = "positive_but_unstable"
        label = "есть ресурс, но совет просит осторожности"
    else:
        code = "balanced"
        label = "ровный, неоднозначный рисунок"

    return {
        "code": code,
        "label": label,
        "positive_count": len(plus_cards),
        "negative_count": len(minus_cards),
        "neutral_count": len(neutral_cards),
        "strongest_card": strongest,
        "hardest_card": hardest,
        "advice_card": advice_card,
    }


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


def _opening_text(spread: Spread, score: int, tags: list[str], pattern: dict[str, Any]) -> str:
    motifs = ", ".join(tags[:3]) if tags else "ясность, внимание и спокойный выбор"

    if spread.code == "quick_answer":
        return (
            f"Это короткий расклад на быстрый взгляд: где находится суть вопроса, что может поддержать и какой шаг выглядит разумным. "
            f"Общий фон: {_score_label(score).lower()}. Главные мотивы: {motifs}."
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


def _synthesis_quick_answer(cards_snapshot: list[dict[str, Any]], score: int, pattern: dict[str, Any]) -> str:
    if len(cards_snapshot) < 3:
        return _synthesis_generic(cards_snapshot, score, pattern)

    core, support, advice = cards_snapshot[:3]
    if support["card"]["score"] < 0:
        support_bridge = (
            "Поддержка здесь выглядит не как легкий ресурс, а как честное обнаружение слабого места: "
            "если его признать, ситуация становится управляемее."
        )
    else:
        support_bridge = "Поддержка уже есть рядом: ее не нужно изобретать, важно просто начать ею пользоваться."

    pattern_comment = _pattern_comment(pattern)
    return (
        f"Суть вопроса задает {_card_line(core)}. "
        f"То есть главный узел сейчас не во всем сразу, а именно в этой теме. "
        f"Вторая карта, {_card_line(support)}, показывает, за счет чего можно не застрять. {support_bridge} "
        f"Совет через карту {_card_line(advice)} переводит расклад в действие. {pattern_comment}"
    )


def _yes_no_direction(score: int, first_score: int) -> str:
    total = score + first_score
    if total >= 4:
        return "скорее да, если действовать спокойно и последовательно"
    if total <= -4:
        return "скорее нет или пока не время давить на ситуацию"
    return "смешанный: многое зависит от условий и следующего шага"


def _synthesis_yes_no(cards_snapshot: list[dict[str, Any]], score: int, pattern: dict[str, Any]) -> str:
    if len(cards_snapshot) < 3:
        return _synthesis_generic(cards_snapshot, score, pattern)

    answer, strengthens, weakens = cards_snapshot[:3]
    direction = _yes_no_direction(score, answer["card"]["score"])
    return (
        f"Главная карта ответа — {_card_line(answer)}. Поэтому общий наклон ответа: {direction}. "
        f"Усиливает ситуацию {_card_line(strengthens)}: это то, на что можно опереться. "
        f"Ослабляет или запутывает ответ {_card_line(weakens)}: эту тему лучше не игнорировать. "
        f"{_pattern_comment(pattern)}"
    )


def _synthesis_two_options(cards_snapshot: list[dict[str, Any]], score: int, pattern: dict[str, Any]) -> str:
    if len(cards_snapshot) < 6:
        return _synthesis_generic(cards_snapshot, score, pattern)

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
        f"Его итоговая линия — {_card_line(b_outcome)}. {lean} {_pattern_comment(pattern)}"
    )


def _synthesis_relationship(cards_snapshot: list[dict[str, Any]], score: int, pattern: dict[str, Any]) -> str:
    if len(cards_snapshot) < 3:
        return _synthesis_generic(cards_snapshot, score, pattern)

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
        f"Финальный акцент — {_card_line(last)} — показывает, во что эта динамика может перейти при текущем поведении. {tone} {_pattern_comment(pattern)}"
    )


def _synthesis_big(cards_snapshot: list[dict[str, Any]], score: int, pattern: dict[str, Any]) -> str:
    if len(cards_snapshot) < 5:
        return _synthesis_generic(cards_snapshot, score, pattern)

    first = cards_snapshot[0]
    strongest = max(cards_snapshot, key=lambda item: item["card"]["score"])
    hardest = min(cards_snapshot, key=lambda item: item["card"]["score"])
    last = cards_snapshot[-1]

    return (
        f"Большой расклад начинается с темы {_card_line(first)}, поэтому ее стоит считать входом во всю картину. "
        f"Самый поддерживающий ресурс здесь — {_card_line(strongest)}. "
        f"Самое чувствительное место — {_card_line(hardest)}; именно там не стоит торопиться или действовать на автомате. "
        f"Финальный акцент {_card_line(last)} показывает направление, в которое складывается история, если ничего резко не ломать. "
        f"{_pattern_comment(pattern)}"
    )


def _synthesis_generic(cards_snapshot: list[dict[str, Any]], score: int, pattern: dict[str, Any]) -> str:
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
        f"Между этими точками и находится главный выбор: что усилить, а что перестать кормить вниманием. {_pattern_comment(pattern)}"
    )


def _pattern_comment(pattern: dict[str, Any]) -> str:
    strongest = pattern.get("strongest_card")
    hardest = pattern.get("hardest_card")
    strongest_text = _card_line(strongest) if strongest else "ресурс не выделен явно"
    hardest_text = _card_line(hardest) if hardest else "напряжение не выделено явно"

    if pattern["code"] == "supportive":
        return f"Плюсовых карт больше, поэтому главный ресурс расклада — {strongest_text}; его стоит использовать осознанно."
    if pattern["code"] == "mixed_with_exit":
        return f"Расклад не полностью ровный, но выход есть: сильнее всего поддерживает {strongest_text}, а осторожности требует {hardest_text}."
    if pattern["code"] == "tense_needs_pause":
        return f"Минусовых карт больше, поэтому важнее сначала снизить давление; самая чувствительная точка — {hardest_text}."
    if pattern["code"] == "positive_but_unstable":
        return f"Ресурс есть, но совет или финальный акцент требуют осторожности: обратите внимание на {hardest_text}."
    return f"Плюсы и напряжения распределены почти ровно: ресурс дает {strongest_text}, а проверку задает {hardest_text}."


def _synthesis_text(spread: Spread, cards_snapshot: list[dict[str, Any]], score: int, pattern: dict[str, Any]) -> str:
    if spread.code == "quick_answer":
        return _synthesis_quick_answer(cards_snapshot, score, pattern)
    if spread.code == "yes_no":
        return _synthesis_yes_no(cards_snapshot, score, pattern)
    if spread.code == "two_options":
        return _synthesis_two_options(cards_snapshot, score, pattern)
    if spread.category == "relationships":
        return _synthesis_relationship(cards_snapshot, score, pattern)
    if spread.category == "big":
        return _synthesis_big(cards_snapshot, score, pattern)
    return _synthesis_generic(cards_snapshot, score, pattern)


def _action_hint(card_snapshot: dict[str, Any]) -> str:
    tags = set(card_snapshot["interpretation"].get("tags") or [])
    meaning = card_snapshot["interpretation"]["short_meaning"]
    card = card_snapshot["card"]

    if tags & {"диалог", "взаимность", "сообщение", "чувства", "романтика", "дружба", "поддержка", "радость"}:
        return "начните с короткого честного разговора или сообщения, где есть один ясный смысл без давления"
    if tags & {"логика", "стратегия", "ясность", "решение", "план", "вопросы", "наблюдение"}:
        return "сформулируйте решение в одном предложении и отделите факт от предположения"
    if tags & {"тревога", "страх", "неясность", "тайна"}:
        return "не принимайте решение на пике тревоги; сначала проверьте, что известно точно, а что только додумано"
    if tags & {"ресурс", "забота", "дом", "опора", "стабильность", "цельность", "завершение"}:
        return "укрепите опору: ресурс, режим, договоренность или простое действие, которое возвращает устойчивость"
    if tags & {"нагрузка", "усталость", "ответственность"}:
        return "снимите одну лишнюю нагрузку и не берите новый долг, пока не освободится место"
    if tags & {"выбор", "перемены", "шанс", "старт"}:
        return "выберите один вариант для проверки и не распыляйте внимание на все дороги сразу"
    if tags & {"границы", "контроль", "защита"}:
        return "обозначьте границу: что вы готовы делать, а что уже выходит за разумную цену"
    if tags & {"мастерство", "команда", "работа", "практика", "рост"}:
        return "переведите идею в рабочий процесс: задача, срок, первый измеримый результат"

    if card.get("arcana") == "major":
        return f"посмотрите, какой этап связан с темой «{meaning}»: что уже пора завершить, принять или назвать своим именем"
    if card.get("suit") == "cups":
        return f"разберитесь, какое чувство стоит за темой «{meaning}», и выразите его спокойнее, чем хочется в первый момент"
    if card.get("suit") == "swords":
        return f"запишите три факта по теме «{meaning}» и отдельно три предположения; решение принимайте только по фактам"
    if card.get("suit") == "wands":
        return f"выберите действие по теме «{meaning}», которое можно начать сегодня без долгой подготовки"
    if card.get("suit") == "pentacles":
        return f"проверьте тему «{meaning}» через практику: деньги, время, договоренность, тело или конкретный результат"

    return f"сведите тему «{meaning}» к одному наблюдаемому шагу, чтобы не раствориться в общих рассуждениях"


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
    action = _action_hint(advice_card)

    if spread.code == "card_of_day":
        return f"На сегодня карта {card_name} предлагает такой фокус: {action}."
    if spread.category == "relationships":
        return (
            f"В отношениях карта {card_name} просит не угадывать за другого человека. "
            f"Лучше сделать так: {action}."
        )
    if spread.category == "work_money":
        return (
            f"В рабочей или денежной теме карта {card_name} просит конкретики: {action}. "
            "Решение должно быть проверяемым, а не только эмоционально убедительным."
        )
    if spread.category == "personal":
        return (
            f"Для личной темы карта {card_name} дает внутренний ориентир: {action}. "
            "Здесь важнее честность с собой, чем быстрый внешний результат."
        )

    if score <= -3:
        return (
            f"Карта {card_name} советует снизить давление и разобраться с темой «{meaning}» без резких решений. "
            "Лучше выбрать действие, которое уменьшает тревогу, а не доказывает правоту."
        )
    if advice_card["card"]["score"] <= -2:
        return (
            f"Карта {card_name} просит не ускорять события и сначала разобраться с темой «{meaning}». "
            "Здесь полезнее убрать лишнее напряжение, чем добавлять новые действия."
        )
    if advice_card["card"]["score"] >= 2:
        return (
            f"Карта {card_name} поддерживает активное действие: {action}. "
            "Это та часть расклада, где можно действовать смелее."
        )
    return f"Карта {card_name} предлагает спокойный практичный ход: {action}."


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
    pattern = _analyze_pattern(cards_snapshot, score)

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

    opening = _opening_text(spread, score, tags, pattern)
    synthesis = _synthesis_text(spread, cards_snapshot, score, pattern)
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
        "pattern": {
            "code": pattern["code"],
            "label": pattern["label"],
            "positive_count": pattern["positive_count"],
            "negative_count": pattern["negative_count"],
            "neutral_count": pattern["neutral_count"],
            "strongest_card": pattern["strongest_card"]["card"]["name_ru"] if pattern["strongest_card"] else None,
            "hardest_card": pattern["hardest_card"]["card"]["name_ru"] if pattern["hardest_card"] else None,
        },
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
