"""
Сервис расчёта потребности в ингредиентах и себестоимости банкета.

Основные формулы (по техническому заданию):
    требуемый объём ингредиента = кол-во порций × норма расхода на 1 порцию;
    стоимость ингредиентов      = Σ (цена × требуемый объём);
    себестоимость банкета        = стоимость ингредиентов
                                   + накладные расходы (% от стоимости продуктов).

Зал у ООО «Агнес» один и собственный, поэтому аренда в себестоимость
не включается.
"""

from core.database import db_cursor
from repositories import banquets as banquets_repo


def calc_ingredient_requirements(banquet_id: int) -> list:
    """Рассчитать потребность в ингредиентах для банкета.

    Возвращает список словарей с полями:
        ingredient_id, name, unit, price, required, cost, stock, shortage.
    Потребность агрегируется по всем блюдам меню.
    """
    with db_cursor() as cur:
        cur.execute(
            "SELECT ing.id AS ingredient_id, ing.name, ing.unit, "
            "       ing.purchase_price AS price, ing.stock, "
            "       SUM(bd.portions * di.norm) AS required "
            "FROM banquet_dishes bd "
            "JOIN dish_ingredients di ON di.dish_id = bd.dish_id "
            "JOIN ingredients ing ON ing.id = di.ingredient_id "
            "WHERE bd.banquet_id = ? "
            "GROUP BY ing.id ORDER BY ing.name",
            (banquet_id,),
        )
        rows = cur.fetchall()

    result = []
    for row in rows:
        required = row["required"] or 0.0
        cost = required * (row["price"] or 0.0)
        shortage = max(0.0, required - (row["stock"] or 0.0))
        result.append({
            "ingredient_id": row["ingredient_id"],
            "name": row["name"],
            "unit": row["unit"],
            "price": row["price"] or 0.0,
            "required": required,
            "cost": cost,
            "stock": row["stock"] or 0.0,
            "shortage": shortage,
        })
    return result


def calc_banquet_cost(banquet_id: int) -> dict:
    """Рассчитать полную себестоимость банкета.

    Возвращает словарь с детализацией:
        ingredients_cost — стоимость продуктов;
        overhead_pct     — процент накладных расходов;
        overhead         — сумма накладных расходов;
        total            — итоговая себестоимость;
        guests           — число гостей;
        cost_per_guest   — себестоимость на одного гостя;
        items            — детализация по ингредиентам.
    """
    banquet = banquets_repo.get(banquet_id)
    if banquet is None:
        raise ValueError("Банкет не найден.")

    items = calc_ingredient_requirements(banquet_id)
    ingredients_cost = sum(item["cost"] for item in items)

    overhead_pct = banquet["overhead_pct"] or 0.0
    overhead = ingredients_cost * overhead_pct / 100.0
    total = ingredients_cost + overhead

    guests = banquet["guests"] or 0
    # Защита от деления на ноль при расчёте себестоимости на гостя.
    cost_per_guest = total / guests if guests > 0 else 0.0

    return {
        "banquet": banquet,
        "ingredients_cost": ingredients_cost,
        "overhead_pct": overhead_pct,
        "overhead": overhead,
        "total": total,
        "guests": guests,
        "cost_per_guest": cost_per_guest,
        "items": items,
    }


def calc_period_usage(date_from: str, date_to: str) -> list:
    """Сводка по использованным продуктам за период.

    Суммирует потребность в каждом ингредиенте по всем банкетам, дата
    проведения которых попадает в интервал [date_from; date_to]. Учитываются
    все статусы, кроме «Отменена».

    :param date_from: начало периода (ГГГГ-ММ-ДД, включительно).
    :param date_to:   конец периода (ГГГГ-ММ-ДД, включительно).
    :return: список словарей: name, unit, required, cost.
    """
    with db_cursor() as cur:
        cur.execute(
            "SELECT ing.name, ing.unit, ing.purchase_price AS price, "
            "       SUM(bd.portions * di.norm) AS required "
            "FROM banquets b "
            "JOIN banquet_dishes bd   ON bd.banquet_id = b.id "
            "JOIN dish_ingredients di ON di.dish_id = bd.dish_id "
            "JOIN ingredients ing     ON ing.id = di.ingredient_id "
            "WHERE b.event_date BETWEEN ? AND ? "
            "  AND b.status <> 'Отменена' "
            "GROUP BY ing.id ORDER BY ing.name",
            (date_from, date_to),
        )
        rows = cur.fetchall()

    result = []
    for row in rows:
        required = row["required"] or 0.0
        result.append({
            "name": row["name"],
            "unit": row["unit"],
            "required": required,
            "cost": required * (row["price"] or 0.0),
        })
    return result
