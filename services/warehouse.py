"""
Сервис склада и закупок.

Реализует:
    * автоматическое формирование заявок на закупку по дефициту
      (остаток < минимальный запас), сгруппированных по поставщикам;
    * оприходование закупки с автоматическим увеличением остатков в БД.
"""

from core.database import db_cursor
from repositories import ingredients as ing_repo
from repositories import purchases as purchases_repo
from core.logger import log_action


def auto_create_purchase_orders() -> list:
    """Сформировать заявки на закупку для всех дефицитных ингредиентов.

    Дефицит = минимальный запас − текущий остаток (заказывается до уровня
    минимального запаса, но не менее 0). Позиции группируются по поставщикам;
    для каждого поставщика создаётся отдельная заявка со статусом «Создана».

    :return: список идентификаторов созданных закупок.
    """
    low = ing_repo.low_stock()
    if not low:
        return []

    # Группировка дефицитных позиций по поставщику.
    by_supplier: dict = {}
    for item in low:
        supplier_id = item["supplier_id"]
        qty = max(0.0, (item["min_stock"] or 0.0) - (item["stock"] or 0.0))
        if qty <= 0:
            continue
        by_supplier.setdefault(supplier_id, []).append(
            (item["id"], qty, item["purchase_price"] or 0.0)
        )

    created = []
    for supplier_id, items in by_supplier.items():
        purchase_id = purchases_repo.create(
            supplier_id, "Автоматически сформирована по дефициту склада", items
        )
        created.append(purchase_id)
    log_action(f"Автоформирование заявок на закупку: создано {len(created)} шт.")
    return created


def receive_purchase(purchase_id: int) -> None:
    """Оприходовать закупку: увеличить остатки ингредиентов и сменить статус.

    Операция выполняется в одной транзакции, чтобы остатки и статус
    обновлялись согласованно.
    """
    with db_cursor(commit=True) as cur:
        # Проверяем текущий статус, чтобы не оприходовать повторно.
        cur.execute("SELECT status FROM purchases WHERE id = ?", (purchase_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError("Закупка не найдена.")
        if row["status"] == "Оприходована":
            raise ValueError("Закупка уже оприходована.")

        cur.execute(
            "SELECT ingredient_id, qty FROM purchase_items WHERE purchase_id = ?",
            (purchase_id,),
        )
        for item in cur.fetchall():
            cur.execute(
                "UPDATE ingredients SET stock = stock + ? WHERE id = ?",
                (item["qty"], item["ingredient_id"]),
            )
        cur.execute(
            "UPDATE purchases SET status = 'Оприходована' WHERE id = ?",
            (purchase_id,),
        )
    log_action(f"Закупка №{purchase_id} оприходована, остатки обновлены")


def change_status(purchase_id: int, status: str) -> None:
    """Сменить статус закупки. При статусе «Оприходована» — обновить остатки."""
    if status == "Оприходована":
        receive_purchase(purchase_id)
    else:
        purchases_repo.set_status(purchase_id, status)
        log_action(f"Закупка №{purchase_id}: статус изменён на «{status}»")
