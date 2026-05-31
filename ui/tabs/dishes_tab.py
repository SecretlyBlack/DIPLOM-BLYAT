"""Вкладка справочника блюд с редактированием рецептуры (норм расхода)."""

import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QTableWidget, QGroupBox,
    QAbstractItemView, QHeaderView, QLabel,
)

from ui.tabs.base import CrudTab
from ui.widgets import cell, make_button, show_error, show_warning
from repositories import dishes as repo
from repositories import ingredients as ingredients_repo
from core.logger import log_action

# Стандартные категории блюд.
CATEGORIES = ["Закуски", "Салаты", "Горячее", "Гарнир", "Десерты", "Напитки"]


class DishDialog(QDialog):
    """Диалог добавления/изменения блюда вместе с рецептурой."""

    def __init__(self, parent=None, row=None):
        super().__init__(parent)
        self.row = row
        self.setWindowTitle("Блюдо и рецептура")
        self.setMinimumSize(560, 480)
        # Кэш ингредиентов для выпадающего списка.
        self._ingredients = ingredients_repo.list_all()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(CATEGORIES)
        form.addRow("Название*:", self.name_edit)
        form.addRow("Категория:", self.category_combo)
        layout.addLayout(form)

        # --- Блок рецептуры ---
        box = QGroupBox("Норма расхода ингредиентов на 1 порцию")
        box_layout = QVBoxLayout(box)

        adder = QHBoxLayout()
        self.ing_combo = QComboBox()
        for ing in self._ingredients:
            self.ing_combo.addItem(f"{ing['name']} ({ing['unit']})", ing["id"])
        self.norm_spin = QDoubleSpinBox()
        self.norm_spin.setRange(0.0, 100000.0)
        self.norm_spin.setDecimals(4)
        self.norm_spin.setValue(0.1)
        adder.addWidget(QLabel("Ингредиент:"))
        adder.addWidget(self.ing_combo, 1)
        adder.addWidget(QLabel("Норма:"))
        adder.addWidget(self.norm_spin)
        adder.addWidget(make_button("Добавить", self._add_ingredient,
                                    "Secondary"))
        box_layout.addLayout(adder)

        self.recipe_table = QTableWidget(0, 3)
        self.recipe_table.setHorizontalHeaderLabels(
            ["Ингредиент", "Ед.", "Норма на порцию"])
        self.recipe_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.recipe_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.recipe_table.verticalHeader().setVisible(False)
        self.recipe_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        box_layout.addWidget(self.recipe_table)
        box_layout.addWidget(
            make_button("Удалить ингредиент", self._remove_ingredient, "Danger"))
        layout.addWidget(box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Текущая рецептура: ingredient_id -> (name, unit, norm).
        self._recipe: dict = {}
        if row is not None:
            self.name_edit.setText(row["name"] or "")
            self.category_combo.setCurrentText(row["category"] or "")
            for item in repo.get_recipe(row["id"]):
                self._recipe[item["ingredient_id"]] = (
                    item["ingredient_name"], item["unit"], item["norm"])
            self._reload_recipe_table()

    # --------------------------------------------------------- рецептура
    def _add_ingredient(self) -> None:
        ing_id = self.ing_combo.currentData()
        if ing_id is None:
            return
        norm = self.norm_spin.value()
        if norm <= 0:
            show_warning(self, "Норма расхода должна быть больше нуля.")
            return
        ing = next((i for i in self._ingredients if i["id"] == ing_id), None)
        if ing is None:
            return
        self._recipe[ing_id] = (ing["name"], ing["unit"], norm)
        self._reload_recipe_table()

    def _remove_ingredient(self) -> None:
        index = self.recipe_table.currentRow()
        ids = list(self._recipe.keys())
        if 0 <= index < len(ids):
            del self._recipe[ids[index]]
            self._reload_recipe_table()

    def _reload_recipe_table(self) -> None:
        self.recipe_table.setRowCount(len(self._recipe))
        for r, (name, unit, norm) in enumerate(self._recipe.values()):
            self.recipe_table.setItem(r, 0, cell(name))
            self.recipe_table.setItem(r, 1, cell(unit))
            self.recipe_table.setItem(r, 2, cell(f"{norm:g}", align_right=True))

    # ------------------------------------------------------------- save
    def _on_save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            show_warning(self, "Укажите название блюда.")
            return
        category = self.category_combo.currentText().strip()
        try:
            if self.row is None:
                dish_id = repo.create(name, category)
                log_action(f"Добавлено блюдо «{name}»")
            else:
                dish_id = self.row["id"]
                repo.update(dish_id, name, category)
                log_action(f"Изменено блюдо «{name}»")
            items = [(ing_id, data[2]) for ing_id, data in self._recipe.items()]
            repo.set_recipe(dish_id, items)
        except sqlite3.IntegrityError:
            show_error(self, "Блюдо с таким названием уже существует.")
            return
        except sqlite3.Error as exc:
            show_error(self, f"Ошибка сохранения: {exc}")
            return
        self.accept()


class DishesTab(CrudTab):
    """Справочник блюд."""

    COLUMNS = ["Название", "Категория", "Ингредиентов в рецептуре"]
    SEARCH_PLACEHOLDER = "Поиск по названию или категории…"
    ADD_LABEL = "Добавить блюдо"

    def load_rows(self, search: str) -> list:
        return repo.list_all(search)

    def fill_row(self, index: int, row) -> None:
        count = len(repo.get_recipe(row["id"]))
        self.table.setItem(index, 0, cell(row["name"]))
        self.table.setItem(index, 1, cell(row["category"] or "—"))
        self.table.setItem(index, 2, cell(str(count), align_right=True))

    def open_editor(self, row) -> bool:
        return DishDialog(self, row).exec() == QDialog.DialogCode.Accepted

    def delete_row(self, row) -> None:
        repo.delete(row["id"])
        log_action(f"Удалено блюдо «{row['name']}»")
