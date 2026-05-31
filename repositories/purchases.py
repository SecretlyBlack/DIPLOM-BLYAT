"""Репозиторий закупок (заявок поставщикам) и их позиций."""

from datetime import datetime

from core.database import db_cursor

# Статусы закупки в порядке жизненного цикла.
STATUSES = ["Создана", "Отправлена поставщику", "Оплачена", "Доставлена", "Оприходована"]


def list_all() -> list:
    """Вернуть список закупок с названием поставщика и суммой."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT p.*, s.name AS supplier_name, "
            "  COALESCE(SUM(pi.qty * pi.price), 0) AS total "
            "FROM purchases p "
            "LEFT JOIN suppliers s ON s.id = p.supplier_id "
            "LEFT JOIN purchase_items pi ON pi.purchase_id = p.id "
            "GROUP BY p.id ORDER BY p.created_at DESC"
        )
        return cur.fetchall()


def get(purchase_id: int):
    """Вернуть одну закупку по идентификатору."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT p.*, s.name AS supplier_name, s.inn AS supplier_inn "
            "FROM purchases p LEFT JOIN suppliers s ON s.id = p.supplier_id "
            "WHERE p.id = ?",
            (purchase_id,),
        )
        return cur.fetchone()


def get_items(purchase_id: int) -> list:
    """Вернуть позиции закупки."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT pi.*, ing.name AS ingredient_name, ing.unit "
            "FROM purchase_items pi "
            "JOIN ingredients ing ON ing.id = pi.ingredient_id "
            "WHERE pi.purchase_id = ? ORDER BY ing.name",
            (purchase_id,),
        )
        return cur.fetchall()


def create(supplier_id, comment, items: list) -> int:
    """Создать закупку с позициями.

    :param items: список кортежей (ingredient_id, qty, price).
    :return: id новой закупки.
    """
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO purchases (supplier_id, status, created_at, comment) "
            "VALUES (?, ?, ?, ?)",
            (supplier_id, "Создана", created_at, comment),
        )
        purchase_id = cur.lastrowid
        for ingredient_id, qty, price in items:
            cur.execute(
                "INSERT INTO purchase_items "
                "(purchase_id, ingredient_id, qty, price) VALUES (?, ?, ?, ?)",
                (purchase_id, ingredient_id, qty, price),
            )
        return purchase_id


def set_status(purchase_id: int, status: str) -> None:
    """Изменить статус закупки."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE purchases SET status = ? WHERE id = ?",
            (status, purchase_id),
        )


def delete(purchase_id: int) -> None:
    """Удалить закупку (вместе с позициями по каскаду)."""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
