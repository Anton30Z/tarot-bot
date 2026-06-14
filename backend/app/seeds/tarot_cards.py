import asyncio
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from app.db import AsyncSessionLocal
from app.models import TarotCard


DECK_CODE = "rider_waite_v1"


def card(
    card_code: str,
    name_ru: str,
    name_en: str,
    arcana: str,
    suit: str | None,
    score: int,
) -> dict[str, Any]:
    return {
        "deck_code": DECK_CODE,
        "card_code": card_code,
        "name_ru": name_ru,
        "name_en": name_en,
        "arcana": arcana,
        "suit": suit,
        "image_url": f"/static/cards/{DECK_CODE}/{card_code}.jpg",
        "score": score,
        "is_active": True,
    }


TAROT_CARDS: list[dict[str, Any]] = [
    card("the_fool", "Шут", "The Fool", "major", None, 2),
    card("the_magician", "Маг", "The Magician", "major", None, 3),
    card("the_high_priestess", "Верховная Жрица", "The High Priestess", "major", None, 1),
    card("the_empress", "Императрица", "The Empress", "major", None, 3),
    card("the_emperor", "Император", "The Emperor", "major", None, 2),
    card("the_hierophant", "Иерофант", "The Hierophant", "major", None, 1),
    card("the_lovers", "Влюбленные", "The Lovers", "major", None, 2),
    card("the_chariot", "Колесница", "The Chariot", "major", None, 3),
    card("strength", "Сила", "Strength", "major", None, 3),
    card("the_hermit", "Отшельник", "The Hermit", "major", None, 0),
    card("wheel_of_fortune", "Колесо Фортуны", "Wheel of Fortune", "major", None, 2),
    card("justice", "Справедливость", "Justice", "major", None, 1),
    card("the_hanged_man", "Повешенный", "The Hanged Man", "major", None, -1),
    card("death", "Смерть", "Death", "major", None, -1),
    card("temperance", "Умеренность", "Temperance", "major", None, 2),
    card("the_devil", "Дьявол", "The Devil", "major", None, -3),
    card("the_tower", "Башня", "The Tower", "major", None, -3),
    card("the_star", "Звезда", "The Star", "major", None, 3),
    card("the_moon", "Луна", "The Moon", "major", None, -1),
    card("the_sun", "Солнце", "The Sun", "major", None, 3),
    card("judgement", "Суд", "Judgement", "major", None, 1),
    card("the_world", "Мир", "The World", "major", None, 3),
    card("ace_of_wands", "Туз Жезлов", "Ace of Wands", "minor", "wands", 3),
    card("two_of_wands", "Двойка Жезлов", "Two of Wands", "minor", "wands", 1),
    card("three_of_wands", "Тройка Жезлов", "Three of Wands", "minor", "wands", 2),
    card("four_of_wands", "Четверка Жезлов", "Four of Wands", "minor", "wands", 3),
    card("five_of_wands", "Пятерка Жезлов", "Five of Wands", "minor", "wands", -1),
    card("six_of_wands", "Шестерка Жезлов", "Six of Wands", "minor", "wands", 3),
    card("seven_of_wands", "Семерка Жезлов", "Seven of Wands", "minor", "wands", 1),
    card("eight_of_wands", "Восьмерка Жезлов", "Eight of Wands", "minor", "wands", 2),
    card("nine_of_wands", "Девятка Жезлов", "Nine of Wands", "minor", "wands", 0),
    card("ten_of_wands", "Десятка Жезлов", "Ten of Wands", "minor", "wands", -2),
    card("page_of_wands", "Паж Жезлов", "Page of Wands", "minor", "wands", 2),
    card("knight_of_wands", "Рыцарь Жезлов", "Knight of Wands", "minor", "wands", 2),
    card("queen_of_wands", "Королева Жезлов", "Queen of Wands", "minor", "wands", 3),
    card("king_of_wands", "Король Жезлов", "King of Wands", "minor", "wands", 3),
    card("ace_of_cups", "Туз Кубков", "Ace of Cups", "minor", "cups", 3),
    card("two_of_cups", "Двойка Кубков", "Two of Cups", "minor", "cups", 3),
    card("three_of_cups", "Тройка Кубков", "Three of Cups", "minor", "cups", 3),
    card("four_of_cups", "Четверка Кубков", "Four of Cups", "minor", "cups", -1),
    card("five_of_cups", "Пятерка Кубков", "Five of Cups", "minor", "cups", -2),
    card("six_of_cups", "Шестерка Кубков", "Six of Cups", "minor", "cups", 2),
    card("seven_of_cups", "Семерка Кубков", "Seven of Cups", "minor", "cups", 0),
    card("eight_of_cups", "Восьмерка Кубков", "Eight of Cups", "minor", "cups", -1),
    card("nine_of_cups", "Девятка Кубков", "Nine of Cups", "minor", "cups", 3),
    card("ten_of_cups", "Десятка Кубков", "Ten of Cups", "minor", "cups", 3),
    card("page_of_cups", "Паж Кубков", "Page of Cups", "minor", "cups", 2),
    card("knight_of_cups", "Рыцарь Кубков", "Knight of Cups", "minor", "cups", 2),
    card("queen_of_cups", "Королева Кубков", "Queen of Cups", "minor", "cups", 3),
    card("king_of_cups", "Король Кубков", "King of Cups", "minor", "cups", 3),
    card("ace_of_swords", "Туз Мечей", "Ace of Swords", "minor", "swords", 2),
    card("two_of_swords", "Двойка Мечей", "Two of Swords", "minor", "swords", -1),
    card("three_of_swords", "Тройка Мечей", "Three of Swords", "minor", "swords", -3),
    card("four_of_swords", "Четверка Мечей", "Four of Swords", "minor", "swords", 0),
    card("five_of_swords", "Пятерка Мечей", "Five of Swords", "minor", "swords", -2),
    card("six_of_swords", "Шестерка Мечей", "Six of Swords", "minor", "swords", 1),
    card("seven_of_swords", "Семерка Мечей", "Seven of Swords", "minor", "swords", -2),
    card("eight_of_swords", "Восьмерка Мечей", "Eight of Swords", "minor", "swords", -2),
    card("nine_of_swords", "Девятка Мечей", "Nine of Swords", "minor", "swords", -3),
    card("ten_of_swords", "Десятка Мечей", "Ten of Swords", "minor", "swords", -3),
    card("page_of_swords", "Паж Мечей", "Page of Swords", "minor", "swords", 1),
    card("knight_of_swords", "Рыцарь Мечей", "Knight of Swords", "minor", "swords", 1),
    card("queen_of_swords", "Королева Мечей", "Queen of Swords", "minor", "swords", 1),
    card("king_of_swords", "Король Мечей", "King of Swords", "minor", "swords", 2),
    card("ace_of_pentacles", "Туз Пентаклей", "Ace of Pentacles", "minor", "pentacles", 3),
    card("two_of_pentacles", "Двойка Пентаклей", "Two of Pentacles", "minor", "pentacles", 1),
    card("three_of_pentacles", "Тройка Пентаклей", "Three of Pentacles", "minor", "pentacles", 2),
    card("four_of_pentacles", "Четверка Пентаклей", "Four of Pentacles", "minor", "pentacles", 0),
    card("five_of_pentacles", "Пятерка Пентаклей", "Five of Pentacles", "minor", "pentacles", -3),
    card("six_of_pentacles", "Шестерка Пентаклей", "Six of Pentacles", "minor", "pentacles", 2),
    card("seven_of_pentacles", "Семерка Пентаклей", "Seven of Pentacles", "minor", "pentacles", 0),
    card("eight_of_pentacles", "Восьмерка Пентаклей", "Eight of Pentacles", "minor", "pentacles", 2),
    card("nine_of_pentacles", "Девятка Пентаклей", "Nine of Pentacles", "minor", "pentacles", 3),
    card("ten_of_pentacles", "Десятка Пентаклей", "Ten of Pentacles", "minor", "pentacles", 3),
    card("page_of_pentacles", "Паж Пентаклей", "Page of Pentacles", "minor", "pentacles", 2),
    card("knight_of_pentacles", "Рыцарь Пентаклей", "Knight of Pentacles", "minor", "pentacles", 1),
    card("queen_of_pentacles", "Королева Пентаклей", "Queen of Pentacles", "minor", "pentacles", 3),
    card("king_of_pentacles", "Король Пентаклей", "King of Pentacles", "minor", "pentacles", 3),
]


async def seed_tarot_cards() -> None:
    async with AsyncSessionLocal() as session:
        for tarot_card in TAROT_CARDS:
            statement = insert(TarotCard).values(**tarot_card)
            update_values = {
                key: statement.excluded[key]
                for key in tarot_card
                if key not in {"deck_code", "card_code"}
            }
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[TarotCard.deck_code, TarotCard.card_code],
                    set_=update_values,
                )
            )
        await session.commit()


def main() -> None:
    if len(TAROT_CARDS) != 78:
        raise RuntimeError(f"Expected 78 cards, got {len(TAROT_CARDS)}")
    asyncio.run(seed_tarot_cards())


if __name__ == "__main__":
    main()
