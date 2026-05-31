"""Репозиторий поставщиков: операции создания, чтения, обновления, удаления."""

from core.database import db_cursor


def list_all(search: str = "") -> list:
    """Вернуть список поставщиков, опционально отфильтрованный по названию/городу."""
    with db_cursor() as cur:
        if search:
            like = f"%{search}%"
            cur.execute(
                "SELECT * FROM suppliers "
                "WHERE name LIKE ? OR city LIKE ? OR inn LIKE ? "
                "ORDER BY name",
                (like, like, like),
            )
        else:
            cur.execute("SELECT * FROM suppliers ORDER BY name")
        return cur.fetchall()


def get(supplier_id: int):
    """Вернуть одного поставщика по идентификатору."""
    with db_cursor() as cur:
        cur.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
        return cur.fetchone()


def create(name, inn, phone, email, contact_person, city, rating) -> int:
    """Создать поставщика. Возвращает id новой записи."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO suppliers "
            "(name, inn, phone, email, contact_person, city, rating) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, inn, phone, email, contact_person, city, rating),
        )
        return cur.lastrowid


def update(supplier_id, name, inn, phone, email, contact_person, city, rating) -> None:
    """Обновить данные поставщика."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE suppliers SET name = ?, inn = ?, phone = ?, email = ?, "
            "contact_person = ?, city = ?, rating = ? WHERE id = ?",
            (name, inn, phone, email, contact_person, city, rating, supplier_id),
        )


def delete(supplier_id: int) -> None:
    """Удалить поставщика по идентификатору."""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
