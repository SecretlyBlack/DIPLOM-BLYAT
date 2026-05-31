"""Репозиторий банкетов (заявок на обслуживание) и состава меню."""

from datetime import datetime

from core.database import db_cursor

# Возможные статусы банкета.
STATUSES = ["Новая", "Подтверждена", "В работе", "Завершена", "Отменена"]


def list_all(search: str = "") -> list:
    """Вернуть список банкетов."""
    with db_cursor() as cur:
        sql = "SELECT b.* FROM banquets b "
        if search:
            like = f"%{search}%"
            cur.execute(
                sql + "WHERE b.client_name LIKE ? OR b.event_date LIKE ? "
                "ORDER BY b.event_date DESC",
                (like, like),
            )
        else:
            cur.execute(sql + "ORDER BY b.event_date DESC")
        return cur.fetchall()


def get(banquet_id: int):
    """Вернуть один банкет по идентификатору."""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM banquets WHERE id = ?", (banquet_id,))
        return cur.fetchone()


def create(client_name, event_date, event_time, guests,
           overhead_pct, status, comment) -> int:
    """Создать банкет. Возвращает id новой записи."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO banquets "
            "(client_name, event_date, event_time, guests, "
            " overhead_pct, status, comment, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (client_name, event_date, event_time, guests,
             overhead_pct, status, comment, created_at),
        )
        return cur.lastrowid


def update(banquet_id, client_name, event_date, event_time, guests,
           overhead_pct, status, comment) -> None:
    """Обновить данные банкета."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE banquets SET client_name = ?, event_date = ?, "
            "event_time = ?, guests = ?, overhead_pct = ?, "
            "status = ?, comment = ? WHERE id = ?",
            (client_name, event_date, event_time, guests,
             overhead_pct, status, comment, banquet_id),
        )


def set_status(banquet_id: int, status: str) -> None:
    """Изменить статус банкета."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE banquets SET status = ? WHERE id = ?", (status, banquet_id)
        )


def delete(banquet_id: int) -> None:
    """Удалить банкет (вместе с составом меню по каскаду)."""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM banquets WHERE id = ?", (banquet_id,))


# ----------------------------- Состав меню -----------------------------

def get_menu(banquet_id: int) -> list:
    """Вернуть состав меню банкета (блюда и число порций)."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT bd.id, bd.dish_id, bd.portions, "
            "       d.name AS dish_name, d.category "
            "FROM banquet_dishes bd "
            "JOIN dishes d ON d.id = bd.dish_id "
            "WHERE bd.banquet_id = ? ORDER BY d.category, d.name",
            (banquet_id,),
        )
        return cur.fetchall()


def set_menu(banquet_id: int, items: list) -> None:
    """Полностью заменить состав меню банкета.

    :param items: список кортежей (dish_id, portions).
    """
    with db_cursor(commit=True) as cur:
        cur.execute(
            "DELETE FROM banquet_dishes WHERE banquet_id = ?", (banquet_id,)
        )
        for dish_id, portions in items:
            cur.execute(
                "INSERT INTO banquet_dishes (banquet_id, dish_id, portions) "
                "VALUES (?, ?, ?)",
                (banquet_id, dish_id, portions),
            )
