"""Репозиторий блюд и норм расхода ингредиентов на 1 порцию."""

from core.database import db_cursor


def list_all(search: str = "") -> list:
    """Вернуть список блюд."""
    with db_cursor() as cur:
        if search:
            like = f"%{search}%"
            cur.execute(
                "SELECT * FROM dishes WHERE name LIKE ? OR category LIKE ? "
                "ORDER BY category, name",
                (like, like),
            )
        else:
            cur.execute("SELECT * FROM dishes ORDER BY category, name")
        return cur.fetchall()


def get(dish_id: int):
    """Вернуть одно блюдо по идентификатору."""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM dishes WHERE id = ?", (dish_id,))
        return cur.fetchone()


def create(name, category) -> int:
    """Создать блюдо. Возвращает id новой записи."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO dishes (name, category) VALUES (?, ?)",
            (name, category),
        )
        return cur.lastrowid


def update(dish_id, name, category) -> None:
    """Обновить данные блюда."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE dishes SET name = ?, category = ? WHERE id = ?",
            (name, category, dish_id),
        )


def delete(dish_id: int) -> None:
    """Удалить блюдо (вместе с его рецептурой по каскаду)."""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))


# ----------------------- Рецептура (нормы расхода) -----------------------

def get_recipe(dish_id: int) -> list:
    """Вернуть рецептуру блюда: ингредиенты и нормы расхода на 1 порцию."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT di.id, di.ingredient_id, di.norm, "
            "       ing.name AS ingredient_name, ing.unit, ing.purchase_price "
            "FROM dish_ingredients di "
            "JOIN ingredients ing ON ing.id = di.ingredient_id "
            "WHERE di.dish_id = ? ORDER BY ing.name",
            (dish_id,),
        )
        return cur.fetchall()


def set_recipe(dish_id: int, items: list) -> None:
    """Полностью заменить рецептуру блюда.

    :param items: список кортежей (ingredient_id, norm).
    """
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM dish_ingredients WHERE dish_id = ?", (dish_id,))
        for ingredient_id, norm in items:
            cur.execute(
                "INSERT INTO dish_ingredients (dish_id, ingredient_id, norm) "
                "VALUES (?, ?, ?)",
                (dish_id, ingredient_id, norm),
            )
