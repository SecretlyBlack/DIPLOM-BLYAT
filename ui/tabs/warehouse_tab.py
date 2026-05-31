"""
Вкладка склада и закупок.

Содержит две области:
    * «Остатки склада» — таблица ингредиентов с цветовой индикацией
      (норма / близко к минимуму / критично) и автоформированием заявок;
    * «Журнал закупок» — список заявок поставщикам, управление статусами
      жизненного цикла и экспорт заявки в PDF.
"""

import pandas as pd

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, QLabel,
    QComboBox, QAbstractItemView, QHeaderView, QGroupBox,
)

from ui.widgets import (
    cell, money, make_button, show_error, show_warning, show_info,
    confirm, ask_save_path,
)
from ui import style
from repositories import ingredients as ing_repo
from repositories import purchases as purchases_repo
from services import warehouse
from services import exporter
from core.logger import log_action


class WarehouseTab(QWidget):
    """Склад (остатки) и журнал закупок."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stock_rows = []
        self._purchase_rows = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        inner = QTabWidget()
        inner.addTab(self._build_stock_tab(), "Остатки склада")
        inner.addTab(self._build_purchases_tab(), "Журнал закупок")
        layout.addWidget(inner)

    # ===================================================== ОСТАТКИ СКЛАДА
    def _build_stock_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        toolbar = QHBoxLayout()
        self.low_only_label = QLabel()
        toolbar.addWidget(self.low_only_label, 1)
        toolbar.addWidget(make_button("Сформировать заявки по дефициту",
                                      self._on_auto_orders))
        toolbar.addWidget(make_button("Экспорт остатков в Excel",
                                      self._on_export_stock, "Secondary"))
        v.addLayout(toolbar)

        # Легенда индикации.
        legend = QHBoxLayout()
        for color, text in [
            (style.COLOR_OK, "Норма"),
            (style.COLOR_WARNING, "Близко к минимуму"),
            (style.COLOR_CRITICAL, "Критично (ниже минимума)"),
        ]:
            lab = QLabel(f"●  {text}")
            lab.setStyleSheet(f"color:{color}; font-weight:bold;")
            legend.addWidget(lab)
        legend.addStretch(1)
        v.addLayout(legend)

        self.stock_table = QTableWidget(0, 6)
        self.stock_table.setHorizontalHeaderLabels(
            ["Ингредиент", "Ед.", "Остаток", "Мин. запас",
             "Дефицит", "Состояние"])
        self.stock_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stock_table.verticalHeader().setVisible(False)
        self.stock_table.setAlternatingRowColors(True)
        self.stock_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.stock_table)
        return w

    def _refresh_stock(self) -> None:
        self._stock_rows = ing_repo.list_all()
        self.stock_table.setRowCount(len(self._stock_rows))
        low_count = 0
        for r, row in enumerate(self._stock_rows):
            stock = row["stock"] or 0.0
            min_stock = row["min_stock"] or 0.0
            shortage = max(0.0, min_stock - stock)
            if stock < min_stock:
                state, color = "Критично", QColor(style.COLOR_CRITICAL)
                low_count += 1
            elif stock < min_stock * 1.2:
                state, color = "Близко к минимуму", QColor(style.COLOR_WARNING)
            else:
                state, color = "Норма", QColor(style.COLOR_OK)

            self.stock_table.setItem(r, 0, cell(row["name"]))
            self.stock_table.setItem(r, 1, cell(row["unit"]))
            self.stock_table.setItem(
                r, 2, cell(f"{stock:g}", align_right=True, color=color,
                           bold=True))
            self.stock_table.setItem(
                r, 3, cell(f"{min_stock:g}", align_right=True))
            self.stock_table.setItem(
                r, 4, cell(f"{shortage:g}" if shortage else "—",
                           align_right=True))
            self.stock_table.setItem(r, 5, cell(state, color=color, bold=True))

        if low_count:
            self.low_only_label.setText(
                f"⚠ Позиций ниже минимального запаса: {low_count}")
            self.low_only_label.setStyleSheet(
                f"color:{style.COLOR_CRITICAL}; font-weight:bold;")
        else:
            self.low_only_label.setText("✓ Все позиции в пределах нормы")
            self.low_only_label.setStyleSheet(
                f"color:{style.COLOR_OK}; font-weight:bold;")

    def _on_auto_orders(self) -> None:
        low = ing_repo.low_stock()
        if not low:
            show_info(self, "Дефицитных позиций нет — заявки не требуются.")
            return
        if not confirm(
                self,
                f"Обнаружено дефицитных позиций: {len(low)}.\n"
                "Сформировать заявки на закупку (с группировкой по поставщикам)?"):
            return
        try:
            created = warehouse.auto_create_purchase_orders()
        except Exception as exc:
            show_error(self, f"Ошибка формирования заявок: {exc}")
            return
        show_info(self, f"Создано заявок на закупку: {len(created)}.")
        self.refresh()

    def _on_export_stock(self) -> None:
        rows = ing_repo.list_all()
        if not rows:
            show_warning(self, "Нет данных для экспорта.")
            return
        df = pd.DataFrame([{
            "Ингредиент": row["name"],
            "Ед. изм.": row["unit"],
            "Цена, ₽": round(row["purchase_price"] or 0, 2),
            "Остаток": row["stock"] or 0,
            "Мин. запас": row["min_stock"] or 0,
            "Поставщик": row["supplier_name"] or "—",
        } for row in rows])
        path = ask_save_path(self, "Сохранить остатки", "Остатки_склада.xlsx",
                             "Файлы Excel (*.xlsx)")
        if not path:
            return
        try:
            exporter.export_dataframe_to_excel(
                df, path, sheet_name="Остатки", title="Остатки склада")
            log_action("Экспорт остатков склада в Excel")
            show_info(self, f"Остатки сохранены:\n{path}")
        except Exception as exc:
            show_error(self, f"Не удалось сохранить файл: {exc}")

    # ===================================================== ЖУРНАЛ ЗАКУПОК
    def _build_purchases_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Статус выбранной заявки:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(purchases_repo.STATUSES)
        toolbar.addWidget(self.status_combo)
        toolbar.addWidget(make_button("Применить статус",
                                      self._on_change_status))
        toolbar.addStretch(1)
        toolbar.addWidget(make_button("Сохранить в PDF",
                                      self._on_export_pdf, "Secondary"))
        toolbar.addWidget(make_button("Удалить", self._on_delete, "Danger"))
        v.addLayout(toolbar)

        # Список закупок.
        self.purchase_table = QTableWidget(0, 5)
        self.purchase_table.setHorizontalHeaderLabels(
            ["№", "Дата", "Поставщик", "Сумма, ₽", "Статус"])
        self.purchase_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.purchase_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.purchase_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.purchase_table.verticalHeader().setVisible(False)
        self.purchase_table.setAlternatingRowColors(True)
        self.purchase_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.purchase_table.itemSelectionChanged.connect(self._on_select)
        v.addWidget(self.purchase_table)

        # Позиции выбранной закупки.
        box = QGroupBox("Позиции выбранной заявки")
        box_v = QVBoxLayout(box)
        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(
            ["Ингредиент", "Ед.", "Кол-во", "Цена, ₽", "Сумма, ₽"])
        self.items_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        box_v.addWidget(self.items_table)
        v.addWidget(box)
        return w

    def _refresh_purchases(self) -> None:
        self._purchase_rows = purchases_repo.list_all()
        self.purchase_table.setRowCount(len(self._purchase_rows))
        for r, row in enumerate(self._purchase_rows):
            color = (QColor(style.COLOR_OK)
                     if row["status"] == "Оприходована" else None)
            self.purchase_table.setItem(r, 0, cell(str(row["id"]),
                                                   align_right=True))
            self.purchase_table.setItem(r, 1, cell(row["created_at"]))
            self.purchase_table.setItem(r, 2, cell(row["supplier_name"] or "—"))
            self.purchase_table.setItem(r, 3, cell(money(row["total"]),
                                                   align_right=True))
            self.purchase_table.setItem(r, 4, cell(row["status"], color=color,
                                                   bold=True))
        self.items_table.setRowCount(0)

    def current_purchase(self):
        index = self.purchase_table.currentRow()
        if 0 <= index < len(self._purchase_rows):
            return self._purchase_rows[index]
        return None

    def _on_select(self) -> None:
        row = self.current_purchase()
        if row is None:
            self.items_table.setRowCount(0)
            return
        # Синхронизируем комбобокс со статусом выбранной заявки.
        idx = self.status_combo.findText(row["status"])
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

        items = purchases_repo.get_items(row["id"])
        self.items_table.setRowCount(len(items))
        for r, item in enumerate(items):
            line = (item["qty"] or 0) * (item["price"] or 0)
            self.items_table.setItem(r, 0, cell(item["ingredient_name"]))
            self.items_table.setItem(r, 1, cell(item["unit"]))
            self.items_table.setItem(r, 2, cell(f"{item['qty']:g}",
                                                align_right=True))
            self.items_table.setItem(r, 3, cell(money(item["price"]),
                                                align_right=True))
            self.items_table.setItem(r, 4, cell(money(line), align_right=True))

    def _on_change_status(self) -> None:
        row = self.current_purchase()
        if row is None:
            show_warning(self, "Выберите заявку для смены статуса.")
            return
        new_status = self.status_combo.currentText()
        if new_status == row["status"]:
            show_info(self, "Статус не изменился.")
            return
        if new_status == "Оприходована":
            if not confirm(
                    self,
                    "При оприходовании остатки ингредиентов будут увеличены "
                    "на количество из заявки. Продолжить?"):
                return
        try:
            warehouse.change_status(row["id"], new_status)
        except ValueError as exc:
            show_warning(self, str(exc))
            return
        except Exception as exc:
            show_error(self, f"Ошибка смены статуса: {exc}")
            return
        self.refresh()
        show_info(self, f"Статус заявки №{row['id']} изменён на «{new_status}».")

    def _on_export_pdf(self) -> None:
        row = self.current_purchase()
        if row is None:
            show_warning(self, "Выберите заявку для экспорта.")
            return
        purchase = purchases_repo.get(row["id"])
        items = purchases_repo.get_items(row["id"])
        if not items:
            show_warning(self, "В заявке нет позиций.")
            return
        path = ask_save_path(self, "Сохранить заявку в PDF",
                             f"Заявка_на_закупку_{row['id']}.pdf",
                             "Документы PDF (*.pdf)")
        if not path:
            return
        try:
            exporter.export_purchase_to_pdf(purchase, items, path)
            log_action(f"Заявка на закупку №{row['id']} сохранена в PDF")
            show_info(self, f"Заявка сохранена:\n{path}")
        except Exception as exc:
            show_error(self, f"Не удалось сохранить PDF: {exc}")

    def _on_delete(self) -> None:
        row = self.current_purchase()
        if row is None:
            show_warning(self, "Выберите заявку для удаления.")
            return
        if confirm(self, f"Удалить заявку на закупку №{row['id']}?"):
            purchases_repo.delete(row["id"])
            log_action(f"Удалена заявка на закупку №{row['id']}")
            self.refresh()

    # --------------------------------------------------------- общий refresh
    def refresh(self) -> None:
        self._refresh_stock()
        self._refresh_purchases()
