"""Вкладка справочника ингредиентов (складских позиций)."""

import sqlite3

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QVBoxLayout,
)

from ui.tabs.base import CrudTab
from ui.widgets import cell, money, show_error, show_warning
from ui import style
from repositories import ingredients as repo
from repositories import suppliers as suppliers_repo
from core.logger import log_action

# Распространённые единицы измерения.
UNITS = ["кг", "л", "шт", "уп", "г", "мл"]


class IngredientDialog(QDialog):
    """Диалог добавления/изменения ингредиента."""

    def __init__(self, parent=None, row=None):
        super().__init__(parent)
        self.row = row
        self.setWindowTitle("Ингредиент")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self.name_edit = QLineEdit()
        self.unit_combo = QComboBox()
        self.unit_combo.setEditable(True)
        self.unit_combo.addItems(UNITS)

        self.price_spin = self._make_spin(max_value=1_000_000, decimals=2)
        self.stock_spin = self._make_spin(max_value=1_000_000, decimals=3)
        self.min_spin = self._make_spin(max_value=1_000_000, decimals=3)

        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("— не задан —", None)
        for sup in suppliers_repo.list_all():
            self.supplier_combo.addItem(sup["name"], sup["id"])

        form.addRow("Название*:", self.name_edit)
        form.addRow("Ед. изм.*:", self.unit_combo)
        form.addRow("Закупочная цена, ₽:", self.price_spin)
        form.addRow("Текущий остаток:", self.stock_spin)
        form.addRow("Минимальный запас:", self.min_spin)
        form.addRow("Поставщик:", self.supplier_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if row is not None:
            self.name_edit.setText(row["name"] or "")
            self.unit_combo.setCurrentText(row["unit"] or "")
            self.price_spin.setValue(row["purchase_price"] or 0.0)
            self.stock_spin.setValue(row["stock"] or 0.0)
            self.min_spin.setValue(row["min_stock"] or 0.0)
            idx = self.supplier_combo.findData(row["supplier_id"])
            if idx >= 0:
                self.supplier_combo.setCurrentIndex(idx)

    @staticmethod
    def _make_spin(max_value: float, decimals: int) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, max_value)
        spin.setDecimals(decimals)
        spin.setGroupSeparatorShown(True)
        return spin

    def _on_save(self) -> None:
        name = self.name_edit.text().strip()
        unit = self.unit_combo.currentText().strip()
        if not name:
            show_warning(self, "Укажите название ингредиента.")
            return
        if not unit:
            show_warning(self, "Укажите единицу измерения.")
            return

        data = (
            name, unit, self.price_spin.value(), self.stock_spin.value(),
            self.min_spin.value(), self.supplier_combo.currentData(),
        )
        try:
            if self.row is None:
                repo.create(*data)
                log_action(f"Добавлен ингредиент «{name}»")
            else:
                repo.update(self.row["id"], *data)
                log_action(f"Изменён ингредиент «{name}»")
        except sqlite3.IntegrityError:
            show_error(self, "Ингредиент с таким названием уже существует.")
            return
        except sqlite3.Error as exc:
            show_error(self, f"Ошибка сохранения: {exc}")
            return
        self.accept()


class IngredientsTab(CrudTab):
    """Справочник ингредиентов с цветовой индикацией остатков."""

    COLUMNS = ["Название", "Ед.", "Цена, ₽", "Остаток",
               "Мин. запас", "Поставщик", "Состояние"]
    SEARCH_PLACEHOLDER = "Поиск по названию…"
    ADD_LABEL = "Добавить ингредиент"

    def load_rows(self, search: str) -> list:
        return repo.list_all(search)

    def fill_row(self, index: int, row) -> None:
        stock = row["stock"] or 0.0
        min_stock = row["min_stock"] or 0.0
        # Определяем состояние и цвет индикации.
        if stock < min_stock:
            state, color = "Критично", QColor(style.COLOR_CRITICAL)
        elif stock < min_stock * 1.2:
            state, color = "Близко к минимуму", QColor(style.COLOR_WARNING)
        else:
            state, color = "Норма", QColor(style.COLOR_OK)

        self.table.setItem(index, 0, cell(row["name"]))
        self.table.setItem(index, 1, cell(row["unit"]))
        self.table.setItem(index, 2, cell(money(row["purchase_price"]),
                                          align_right=True))
        self.table.setItem(index, 3, cell(f"{stock:g}", align_right=True,
                                          color=color, bold=True))
        self.table.setItem(index, 4, cell(f"{min_stock:g}", align_right=True))
        self.table.setItem(index, 5, cell(row["supplier_name"] or "—"))
        self.table.setItem(index, 6, cell(state, color=color, bold=True))

    def open_editor(self, row) -> bool:
        return IngredientDialog(self, row).exec() == QDialog.DialogCode.Accepted

    def delete_row(self, row) -> None:
        repo.delete(row["id"])
        log_action(f"Удалён ингредиент «{row['name']}»")
