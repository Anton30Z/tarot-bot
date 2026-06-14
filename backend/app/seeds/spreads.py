import asyncio
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from app.db import AsyncSessionLocal
from app.models import Spread


def positions(*names: str) -> list[dict[str, Any]]:
    return [{"index": index, "name": name} for index, name in enumerate(names, start=1)]


SPREADS: list[dict[str, Any]] = [
    {
        "code": "card_of_day",
        "name": "Карта дня",
        "category": "free",
        "description": "Короткий ориентир на день: настроение, совет и главный фокус.",
        "price": 0,
        "cards_count": 1,
        "cooldown_hours": 24,
        "positions_jsonb": positions("Главный совет дня"),
    },
    {
        "code": "quick_answer",
        "name": "Быстрый ответ",
        "category": "free",
        "description": "Три карты для быстрого взгляда на ситуацию без лишней драматизации.",
        "price": 0,
        "cards_count": 3,
        "cooldown_hours": 24,
        "positions_jsonb": positions("Суть вопроса", "Что помогает", "Совет"),
    },
    {
        "code": "yes_no",
        "name": "Да или нет",
        "category": "free",
        "description": "Мягкий ответ на закрытый вопрос с пояснением, что влияет на исход.",
        "price": 0,
        "cards_count": 3,
        "cooldown_hours": 24,
        "positions_jsonb": positions("Ответ", "Что усиливает", "Что ослабляет"),
    },
    {
        "code": "feelings",
        "name": "Что он/она чувствует",
        "category": "relationships",
        "description": "Расклад о чувствах, скрытых мотивах и возможном шаге в общении.",
        "price": 149,
        "cards_count": 3,
        "cooldown_hours": 24,
        "positions_jsonb": positions("Внешнее поведение", "Внутренние чувства", "Ближайший импульс"),
    },
    {
        "code": "relationship_future",
        "name": "Будущее отношений",
        "category": "relationships",
        "description": "Показывает текущее состояние пары, напряжение и вероятное развитие.",
        "price": 199,
        "cards_count": 5,
        "cooldown_hours": 48,
        "positions_jsonb": positions("Сейчас между вами", "Ваш вклад", "Вклад партнера", "Главный вызов", "Ближайшее развитие"),
    },
    {
        "code": "reconciliation",
        "name": "Примирение",
        "category": "relationships",
        "description": "Помогает понять, есть ли пространство для сближения и какой шаг уместен.",
        "price": 199,
        "cards_count": 5,
        "cooldown_hours": 48,
        "positions_jsonb": positions("Причина дистанции", "Что осталось живым", "Что мешает", "Что поможет", "Вероятный итог"),
    },
    {
        "code": "hidden_thoughts",
        "name": "Скрытые мысли",
        "category": "relationships",
        "description": "Аккуратный взгляд на то, что человек может не проговаривать открыто.",
        "price": 149,
        "cards_count": 4,
        "cooldown_hours": 24,
        "positions_jsonb": positions("Что показывает", "Что скрывает", "Чего боится", "Что может сделать"),
    },
    {
        "code": "finances",
        "name": "Финансы",
        "category": "work_money",
        "description": "Обзор денежной ситуации, рисков и полезного практичного шага.",
        "price": 199,
        "cards_count": 5,
        "cooldown_hours": 48,
        "positions_jsonb": positions("Текущая ситуация", "Источник напряжения", "Возможность", "Риск", "Совет"),
    },
    {
        "code": "career",
        "name": "Карьера",
        "category": "work_money",
        "description": "Расклад о профессиональном движении, сильной стороне и ближайшем шаге.",
        "price": 199,
        "cards_count": 5,
        "cooldown_hours": 48,
        "positions_jsonb": positions("Где вы сейчас", "Сильная сторона", "Что тормозит", "Куда расти", "Следующий шаг"),
    },
    {
        "code": "change_job",
        "name": "Смена работы",
        "category": "work_money",
        "description": "Помогает взвесить текущую работу, перспективу перемен и осторожный совет.",
        "price": 249,
        "cards_count": 6,
        "cooldown_hours": 72,
        "positions_jsonb": positions("Текущая работа", "Что не устраивает", "Что можно получить", "Что можно потерять", "Скрытый фактор", "Совет"),
    },
    {
        "code": "near_future",
        "name": "Ближайшее будущее",
        "category": "future_choice",
        "description": "Короткий прогноз на ближайший период без обещаний точного будущего.",
        "price": 199,
        "cards_count": 5,
        "cooldown_hours": 48,
        "positions_jsonb": positions("Главная тема", "Что приходит", "Что уходит", "На что обратить внимание", "Итог периода"),
    },
    {
        "code": "two_options",
        "name": "Два варианта",
        "category": "future_choice",
        "description": "Сравнивает две дороги и помогает увидеть цену каждого выбора.",
        "price": 249,
        "cards_count": 6,
        "cooldown_hours": 48,
        "positions_jsonb": positions("Вариант A: плюс", "Вариант A: риск", "Вариант A: итог", "Вариант B: плюс", "Вариант B: риск", "Вариант B: итог"),
    },
    {
        "code": "month_forecast",
        "name": "Прогноз на месяц",
        "category": "future_choice",
        "description": "Общий ритм месяца: возможности, напряжение, ресурс и совет.",
        "price": 299,
        "cards_count": 7,
        "cooldown_hours": 168,
        "positions_jsonb": positions("Фон месяца", "Любовь", "Работа", "Деньги", "Ресурс", "Риск", "Главный совет"),
    },
    {
        "code": "cards_advice",
        "name": "Совет карт",
        "category": "personal",
        "description": "Личный совет, который помогает спокойнее посмотреть на ситуацию.",
        "price": 149,
        "cards_count": 3,
        "cooldown_hours": 24,
        "positions_jsonb": positions("Что принять", "Что отпустить", "Что сделать"),
    },
    {
        "code": "blockers",
        "name": "Что меня блокирует",
        "category": "personal",
        "description": "Показывает внутреннее препятствие, его источник и бережный способ движения.",
        "price": 199,
        "cards_count": 5,
        "cooldown_hours": 48,
        "positions_jsonb": positions("Внешний блок", "Внутренний блок", "Источник", "Что поддержит", "Первый шаг"),
    },
    {
        "code": "hidden_resource",
        "name": "Скрытый ресурс",
        "category": "personal",
        "description": "Раскрывает качество или опору, которые уже есть, но пока используются не полностью.",
        "price": 199,
        "cards_count": 4,
        "cooldown_hours": 48,
        "positions_jsonb": positions("Ваш ресурс", "Где он скрыт", "Как его включить", "Что изменится"),
    },
    {
        "code": "full_relationship",
        "name": "Большой расклад на отношения",
        "category": "big",
        "description": "Подробный взгляд на связь, динамику, вызовы и вероятное развитие.",
        "price": 499,
        "cards_count": 10,
        "cooldown_hours": 168,
        "positions_jsonb": positions(
            "Вы",
            "Партнер",
            "Основа связи",
            "Сильная сторона",
            "Слабое место",
            "Скрытый мотив",
            "Ближайший шаг",
            "Что поможет",
            "Что помешает",
            "Итог",
        ),
    },
    {
        "code": "full_month",
        "name": "Большой расклад на месяц",
        "category": "big",
        "description": "Развернутый обзор месяца по главным сферам и внутреннему состоянию.",
        "price": 499,
        "cards_count": 10,
        "cooldown_hours": 168,
        "positions_jsonb": positions(
            "Фон месяца",
            "Главная задача",
            "Любовь",
            "Работа",
            "Деньги",
            "Здоровье ритма",
            "Ресурс",
            "Риск",
            "Неожиданность",
            "Итог",
        ),
    },
    {
        "code": "celtic_cross",
        "name": "Кельтский крест",
        "category": "big",
        "description": "Классический глубокий расклад для сложной ситуации и выбора направления.",
        "price": 599,
        "cards_count": 10,
        "cooldown_hours": 168,
        "positions_jsonb": positions(
            "Суть ситуации",
            "Перекрестное влияние",
            "Основа",
            "Прошлое",
            "Сознательная цель",
            "Ближайшее развитие",
            "Ваша позиция",
            "Окружение",
            "Надежды и страхи",
            "Итог",
        ),
    },
]


async def seed_spreads() -> None:
    async with AsyncSessionLocal() as session:
        for spread in SPREADS:
            values = {
                **spread,
                "currency": "RUB",
                "is_active": True,
            }
            statement = insert(Spread).values(**values)
            update_values = {
                key: statement.excluded[key]
                for key in values
                if key != "code"
            }
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[Spread.code],
                    set_=update_values,
                )
            )
        await session.commit()


def main() -> None:
    asyncio.run(seed_spreads())


if __name__ == "__main__":
    main()
