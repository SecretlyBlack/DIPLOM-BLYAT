"""
Вкладка управления банкетами.

Позволяет создавать заявки на банкет (дата, время, гости, меню),
автоматически рассчитывать потребность в ингредиентах и себестоимость,
а также экспортировать калькуляцию в Excel.
"""

import sqlite3

from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtWidgets import (
    QWidget, QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QDateEdit, QTimeEdit, QTextEdit, QDialogButtonBox,
    QVBoxLayout, QHBoxLayout, QTableWidget, QGroupBox, QAbstractItemView,
    QHeaderView, QLabel, QSplitter, QGridLayout,
)

from ui.widgets import (
    cell, money, make_button, show_error, show_warning, show_info,
    confirm, ask_save_path,
)
from repositories import banquets as repo
from repositories import dishes as dishes_repo
from services import costing
from services import exporter
from core import config
from core.logger import log_action


class BanquetDialog(QDialog):
    """Диалог создания/изменения заявки на банкет с выбором меню."""

    def __init__(self, parent=None, row=None):
        super().__init__(parent)
        self.row = row
        self.setWindowTitle("Заявка на банкет")
        self.setMinimumSize(620, 560)
        self._dishes = dishes_repo.list_all()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self.client_edit = QLineEdit()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(16, 0))

        self.guests_spin = QSpinBox()
        self.guests_spin.setRange(1, 100000)
        self.guests_spin.setValue(50)
        self.guests_spin.valueChanged.connect(self._on_guests_changed)

        self.overhead_spin = QDoubleSpinBox()
        self.overhead_spin.setRange(0.0, 1000.0)
        self.overhead_spin.setDecimals(1)
        self.overhead_spin.setSuffix(" %")
        self.overhead_spin.setValue(config.get_overhead_pct())

        self.status_combo = QComboBox()
        self.status_combo.addItems(repo.STATUSES)

        self.comment_edit = QTextEdit()
        self.comment_edit.setMaximumHeight(60)

        form.addRow("Клиент*:", self.client_edit)
        form.addRow("Дата проведения:", self.date_edit)
        form.addRow("Время:", self.time_edit)
        form.addRow("Количество гостей*:", self.guests_spin)
        form.addRow("Накладные расходы:", self.overhead_spin)
        form.addRow("Статус:", self.status_combo)
        form.addRow("Комментарий:", self.comment_edit)
        layout.addLayout(form)

        # --- Меню банкета ---
        box = QGroupBox("Меню банкета (блюда и количество порций)")
        box_layout = QVBoxLayout(box)
        adder = QHBoxLayout()
        self.dish_combo = QComboBox()
        for dish in self._dishes:
            label = dish["name"]
            if dish["category"]:
                label += f" — {dish['category']}"
            self.dish_combo.addItem(label, dish["id"])
        self.portions_spin = QSpinBox()
        self.portions_spin.setRange(1, 100000)
        self.portions_spin.setValue(self.guests_spin.value())
        adder.addWidget(QLabel("Блюдо:"))
        adder.addWidget(self.dish_combo, 1)
        adder.addWidget(QLabel("Порций:"))
        adder.addWidget(self.portions_spin)
        adder.addWidget(make_button("Добавить", self._add_dish, "Secondary"))
        box_layout.addLayout(adder)

        self.menu_table = QTableWidget(0, 3)
        self.menu_table.setHorizontalHeaderLabels(
            ["Блюдо", "Категория", "Порций"])
        self.menu_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.menu_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.menu_table.verticalHeader().setVisible(False)
        self.menu_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        box_layout.addWidget(self.menu_table)
        box_layout.addWidget(
            make_button("Убрать блюдо", self._remove_dish, "Danger"))
        layout.addWidget(box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Меню: dish_id -> (name, category, portions).
        self._menu: dict = {}
        if row is not None:
            self._load_existing(row)

    def _load_existing(self, row) -> None:
        self.client_edit.setText(row["client_name"] or "")
        qd = QDate.fromString(row["event_date"], "yyyy-MM-dd")
        if qd.isValid():
            self.date_edit.setDate(qd)
        qt = QTime.fromString(row["event_time"] or "", "HH:mm")
        if qt.isValid():
            self.time_edit.setTime(qt)
        self.guests_spin.setValue(row["guests"] or 1)
        self.overhead_spin.setValue(row["overhead_pct"] or 0.0)
        sidx = self.status_combo.findText(row["status"] or "")
        if sidx >= 0:
            self.status_combo.setCurrentIndex(sidx)
        self.comment_edit.setPlainText(row["comment"] or "")
        for item in repo.get_menu(row["id"]):
            self._menu[item["dish_id"]] = (
                item["dish_name"], item["category"], item["portions"])
        self._reload_menu_table()

    def _on_guests_changed(self, value: int) -> None:
        """При изменении числа гостей подставлять его как порций по умолчанию."""
        self.portions_spin.setValue(value)

    # ----------------------------------------------------------- меню
    def _add_dish(self) -> None:
        dish_id = self.dish_combo.currentData()
        if dish_id is None:
            return
        dish = next((d for d in self._dishes if d["id"] == dish_id), None)
        if dish is None:
            return
        self._menu[dish_id] = (
            dish["name"], dish["category"], self.portions_spin.value())
        self._reload_menu_table()

    def _remove_dish(self) -> None:
        index = self.menu_table.currentRow()
        ids = list(self._menu.keys())
        if 0 <= index < len(ids):
            del self._menu[ids[index]]
            self._reload_menu_table()

    def _reload_menu_table(self) -> None:
        self.menu_table.setRowCount(len(self._menu))
        for r, (name, category, portions) in enumerate(self._menu.values()):
            self.menu_table.setItem(r, 0, cell(name))
            self.menu_table.setItem(r, 1, cell(category or "—"))
            self.menu_table.setItem(r, 2, cell(str(portions), align_right=True))

    # ----------------------------------------------------------- save
    def _on_save(self) -> None:
        client = self.client_edit.text().strip()
        if not client:
            show_warning(self, "Укажите наименование клиента.")
            return
        guests = self.guests_spin.value()

        if not self._menu:
            if not confirm(self, "Меню не задано. Сохранить заявку без меню?"):
                return

        data = (
            client,
            self.date_edit.date().toString("yyyy-MM-dd"),
            self.time_edit.time().toString("HH:mm"),
            guests, self.overhead_spin.value(),
            self.status_combo.currentText(),
            self.comment_edit.toPlainText().strip(),
        )
        try:
            if self.row is None:
                banquet_id = repo.create(*data)
                log_action(f"Создана заявка на банкет «{client}»")
            else:
                banquet_id = self.row["id"]
                repo.update(banquet_id, *data)
                log_action(f"Изменена заявка на банкет «{client}»")
            menu = [(dish_id, info[2]) for dish_id, info in self._menu.items()]
            repo.set_menu(banquet_id, menu)
        except sqlite3.Error as exc:
            show_error(self, f"Ошибка сохранения: {exc}")
            return
        self.accept()


class BanquetsTab(QWidget):
    """Управление банкетами и расчёт себестоимости."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по клиенту или дате…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.refresh)
        toolbar.addWidget(QLabel("🔍"))
        toolbar.addWidget(self.search_edit, 1)
        toolbar.addWidget(make_button("Создать заявку", self._on_add))
        toolbar.addWidget(make_button("Изменить", self._on_edit, "Secondary"))
        toolbar.addWidget(make_button("Удалить", self._on_delete, "Danger"))
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Список банкетов.
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Клиент", "Дата", "Время", "Гостей"])
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.doubleClicked.connect(self._on_edit)
        splitter.addWidget(self.table)

        # Панель расчёта себестоимости.
        splitter.addWidget(self._build_cost_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

    def _build_cost_panel(self) -> QWidget:
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setContentsMargins(8, 0, 0, 0)

        self.cost_title = QLabel("Калькуляция себестоимости")
        self.cost_title.setStyleSheet("font-weight:bold; font-size:14px;")
        v.addWidget(self.cost_title)

        # Сводные показатели.
        grid_box = QGroupBox("Сводка")
        grid = QGridLayout(grid_box)
        self._summary_labels = {}
        fields = [
            ("ingredients_cost", "Стоимость продуктов, ₽"),
            ("overhead", "Накладные расходы, ₽"),
            ("total", "ИТОГО себестоимость, ₽"),
            ("cost_per_guest", "На одного гостя, ₽"),
        ]
        for r, (key, title) in enumerate(fields):
            grid.addWidget(QLabel(title + ":"), r, 0)
            value = QLabel("—")
            value.setAlignment(Qt.AlignmentFlag.AlignRight
                               | Qt.AlignmentFlag.AlignVCenter)
            if key in ("total", "cost_per_guest"):
                value.setObjectName("SummaryValue")
            self._summary_labels[key] = value
            grid.addWidget(value, r, 1)
        v.addWidget(grid_box)

        # Детализация потребности в ингредиентах.
        v.addWidget(QLabel("Потребность в ингредиентах:"))
        self.req_table = QTableWidget(0, 5)
        self.req_table.setHorizontalHeaderLabels(
            ["Ингредиент", "Ед.", "Требуется", "Остаток", "Стоимость, ₽"])
        self.req_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.req_table.verticalHeader().setVisible(False)
        self.req_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.req_table)

        v.addWidget(make_button("Экспорт калькуляции в Excel",
                                self._on_export, "Secondary"))
        return panel

    # --------------------------------------------------------- data
    def refresh(self) -> None:
        search = self.search_edit.text().strip()
        self._rows = repo.list_all(search)
        self.table.setRowCount(len(self._rows))
        for r, row in enumerate(self._rows):
            self.table.setItem(r, 0, cell(row["client_name"]))
            self.table.setItem(r, 1, cell(row["event_date"]))
            self.table.setItem(r, 2, cell(row["event_time"] or "—"))
            self.table.setItem(r, 3, cell(str(row["guests"]), align_right=True))
        self._clear_cost_panel()

    def current_row(self):
        index = self.table.currentRow()
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    def _on_select(self) -> None:
        row = self.current_row()
        if row is None:
            self._clear_cost_panel()
            return
        self._show_cost(row["id"])

    def _clear_cost_panel(self) -> None:
        self.cost_title.setText("Калькуляция себестоимости")
        for label in self._summary_labels.values():
            label.setText("—")
        self.req_table.setRowCount(0)

    def _show_cost(self, banquet_id: int) -> None:
        try:
            cost = costing.calc_banquet_cost(banquet_id)
        except Exception as exc:           # расчёт не должен ронять интерфейс
            show_error(self, f"Ошибка расчёта: {exc}")
            return
        banquet = cost["banquet"]
        self.cost_title.setText(
            f"Калькуляция: {banquet['client_name']} ({banquet['event_date']})")
        self._summary_labels["ingredients_cost"].setText(
            money(cost["ingredients_cost"]))
        self._summary_labels["overhead"].setText(
            f"{money(cost['overhead'])}  ({cost['overhead_pct']:.0f}%)")
        self._summary_labels["total"].setText(money(cost["total"]))
        self._summary_labels["cost_per_guest"].setText(
            money(cost["cost_per_guest"]))

        items = cost["items"]
        self.req_table.setRowCount(len(items))
        for r, item in enumerate(items):
            self.req_table.setItem(r, 0, cell(item["name"]))
            self.req_table.setItem(r, 1, cell(item["unit"]))
            self.req_table.setItem(
                r, 2, cell(f"{item['required']:g}", align_right=True))
            self.req_table.setItem(
                r, 3, cell(f"{item['stock']:g}", align_right=True))
            self.req_table.setItem(
                r, 4, cell(money(item["cost"]), align_right=True))

    # --------------------------------------------------------- actions
    def _on_add(self) -> None:
        if BanquetDialog(self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_edit(self, *args) -> None:
        row = self.current_row()
        if row is None:
            show_warning(self, "Выберите банкет для изменения.")
            return
        full = repo.get(row["id"])
        if BanquetDialog(self, full).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_delete(self) -> None:
        row = self.current_row()
        if row is None:
            show_warning(self, "Выберите банкет для удаления.")
            return
        if confirm(self, f"Удалить заявку «{row['client_name']}»?"):
            repo.delete(row["id"])
            log_action(f"Удалена заявка на банкет «{row['client_name']}»")
            self.refresh()

    def _on_export(self) -> None:
        row = self.current_row()
        if row is None:
            show_warning(self, "Выберите банкет для экспорта.")
            return
        try:
            cost = costing.calc_banquet_cost(row["id"])
        except Exception as exc:
            show_error(self, f"Ошибка расчёта: {exc}")
            return
        default = f"Калькуляция_{row['client_name']}.xlsx".replace(" ", "_")
        path = ask_save_path(self, "Сохранить калькуляцию", default,
                             "Файлы Excel (*.xlsx)")
        if not path:
            return
        try:
            exporter.export_banquet_cost_to_excel(cost, path)
            log_action(f"Экспорт калькуляции банкета «{row['client_name']}» в Excel")
            show_info(self, f"Калькуляция сохранена:\n{path}")
        except Exception as exc:
            show_error(self, f"Не удалось сохранить файл: {exc}")
