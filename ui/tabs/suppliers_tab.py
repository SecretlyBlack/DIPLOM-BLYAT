"""Вкладка справочника поставщиков."""

import sqlite3

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox, QDialogButtonBox,
    QVBoxLayout,
)

from ui.tabs.base import CrudTab
from ui.widgets import cell, show_error, show_warning
from repositories import suppliers as repo
from core.logger import log_action


class SupplierDialog(QDialog):
    """Диалог добавления/изменения поставщика."""

    def __init__(self, parent=None, row=None):
        super().__init__(parent)
        self.row = row
        self.setWindowTitle("Поставщик")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self.name_edit = QLineEdit()
        self.inn_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.contact_edit = QLineEdit()
        self.city_edit = QLineEdit()
        self.rating_spin = QDoubleSpinBox()
        self.rating_spin.setRange(0.0, 5.0)
        self.rating_spin.setSingleStep(0.1)
        self.rating_spin.setDecimals(1)

        form.addRow("Название*:", self.name_edit)
        form.addRow("ИНН:", self.inn_edit)
        form.addRow("Телефон:", self.phone_edit)
        form.addRow("E-mail:", self.email_edit)
        form.addRow("Контактное лицо:", self.contact_edit)
        form.addRow("Город:", self.city_edit)
        form.addRow("Рейтинг (0–5):", self.rating_spin)
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
            self.inn_edit.setText(row["inn"] or "")
            self.phone_edit.setText(row["phone"] or "")
            self.email_edit.setText(row["email"] or "")
            self.contact_edit.setText(row["contact_person"] or "")
            self.city_edit.setText(row["city"] or "")
            self.rating_spin.setValue(row["rating"] or 0.0)

    def _on_save(self) -> None:
        """Проверить ввод и сохранить поставщика."""
        name = self.name_edit.text().strip()
        if not name:
            show_warning(self, "Укажите название поставщика.")
            return

        inn = self.inn_edit.text().strip()
        if inn and (not inn.isdigit() or len(inn) not in (10, 12)):
            show_warning(self, "ИНН должен содержать 10 или 12 цифр.")
            return

        data = (
            name, inn, self.phone_edit.text().strip(),
            self.email_edit.text().strip(), self.contact_edit.text().strip(),
            self.city_edit.text().strip(), self.rating_spin.value(),
        )
        try:
            if self.row is None:
                repo.create(*data)
                log_action(f"Добавлен поставщик «{name}»")
            else:
                repo.update(self.row["id"], *data)
                log_action(f"Изменён поставщик «{name}»")
        except sqlite3.IntegrityError:
            show_error(self, "Поставщик с таким названием уже существует.")
            return
        except sqlite3.Error as exc:
            show_error(self, f"Ошибка сохранения: {exc}")
            return
        self.accept()


class SuppliersTab(CrudTab):
    """Справочник поставщиков."""

    COLUMNS = ["Название", "ИНН", "Телефон", "E-mail",
               "Контактное лицо", "Город", "Рейтинг"]
    SEARCH_PLACEHOLDER = "Поиск по названию, городу или ИНН…"
    ADD_LABEL = "Добавить поставщика"

    def load_rows(self, search: str) -> list:
        return repo.list_all(search)

    def fill_row(self, index: int, row) -> None:
        self.table.setItem(index, 0, cell(row["name"]))
        self.table.setItem(index, 1, cell(row["inn"]))
        self.table.setItem(index, 2, cell(row["phone"]))
        self.table.setItem(index, 3, cell(row["email"]))
        self.table.setItem(index, 4, cell(row["contact_person"]))
        self.table.setItem(index, 5, cell(row["city"]))
        self.table.setItem(index, 6, cell(f"{row['rating']:.1f}",
                                          align_right=True))

    def open_editor(self, row) -> bool:
        return SupplierDialog(self, row).exec() == QDialog.DialogCode.Accepted

    def delete_row(self, row) -> None:
        repo.delete(row["id"])
        log_action(f"Удалён поставщик «{row['name']}»")
