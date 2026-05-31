"""Репозиторий ингредиентов (складских позиций)."""

from core.database import db_cursor


def list_all(search: str = "") -> list:
    """Вернуть список ингредиентов с названием поставщика."""
    with db_cursor() as cur:
        sql = (
            "SELECT i.*, s.name AS supplier_name "
            "FROM ingredients i "
            "LEFT JOIN suppliers s ON s.id = i.supplier_id "
        )
        if search:
            like = f"%{search}%"
            cur.execute(sql + "WHERE i.name LIKE ? ORDER BY i.name", (like,))
        else:
            cur.execute(sql + "ORDER BY i.name")
        return cur.fetchall()


def get(ingredient_id: int):
    """Вернуть один ингредиент по идентификатору."""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,))
        return cur.fetchone()


def create(name, unit, purchase_price, stock, min_stock, supplier_id) -> int:
    """Создать ингредиент. Возвращает id новой записи."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO ingredients "
            "(name, unit, purchase_price, stock, min_stock, supplier_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, unit, purchase_price, stock, min_stock, supplier_id),
        )
        return cur.lastrowid


def update(ingredient_id, name, unit, purchase_price, stock, min_stock, supplier_id) -> None:
    """Обновить данные ингредиента."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE ingredients SET name = ?, unit = ?, purchase_price = ?, "
            "stock = ?, min_stock = ?, supplier_id = ? WHERE id = ?",
            (name, unit, purchase_price, stock, min_stock, supplier_id, ingredient_id),
        )


def delete(ingredient_id: int) -> None:
    """Удалить ингредиент по идентификатору."""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))


def add_stock(ingredient_id: int, qty: float) -> None:
    """Увеличить остаток ингредиента (используется при оприходовании закупки)."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE ingredients SET stock = stock + ? WHERE id = ?",
            (qty, ingredient_id),
        )


def low_stock() -> list:
    """Вернуть ингредиенты, остаток которых ниже минимального запаса."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT i.*, s.name AS supplier_name "
            "FROM ingredients i "
            "LEFT JOIN suppliers s ON s.id = i.supplier_id "
            "WHERE i.stock < i.min_stock ORDER BY i.name"
        )
        return cur.fetchall()
