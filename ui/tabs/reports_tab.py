"""
Вкладка отчётности, настроек и журнала действий.

Объединяет три раздела:
    * «Сводка по продуктам» — расход ингредиентов за выбранный период
      с возможностью экспорта в Excel;
    * «Настройки» — процент накладных расходов, реквизиты организации,
      имя текущего пользователя (для журнала);
    * «Журнал действий» — хронология операций пользователя.
"""

import pandas as pd

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, QLabel,
    QDateEdit, QDoubleSpinBox, QLineEdit, QFormLayout, QGroupBox,
    QAbstractItemView, QHeaderView,
)

from ui.widgets import (
    cell, money, make_button, show_error, show_warning, show_info,
    ask_save_path,
)
from services import costing
from services import exporter
from core import config
from core.logger import log_action, get_logs


class ReportsTab(QWidget):
    """Отчёты, настройки и журнал действий."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._usage_rows = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        inner = QTabWidget()
        inner.addTab(self._build_usage_tab(), "Сводка по продуктам")
        inner.addTab(self._build_settings_tab(), "Настройки")
        inner.addTab(self._build_logs_tab(), "Журнал действий")
        inner.currentChanged.connect(lambda *_: self.refresh())
        layout.addWidget(inner)

    # ============================================== СВОДКА ПО ПРОДУКТАМ
    def _build_usage_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Период с:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        toolbar.addWidget(self.date_from)
        toolbar.addWidget(QLabel("по:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setDate(QDate.currentDate().addMonths(1))
        toolbar.addWidget(self.date_to)
        toolbar.addWidget(make_button("Сформировать", self._build_usage))
        toolbar.addStretch(1)
        toolbar.addWidget(make_button("Экспорт в Excel",
                                      self._on_export_usage, "Secondary"))
        v.addLayout(toolbar)

        self.usage_table = QTableWidget(0, 4)
        self.usage_table.setHorizontalHeaderLabels(
            ["Ингредиент", "Ед.", "Израсходовано", "Стоимость, ₽"])
        self.usage_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.usage_table.verticalHeader().setVisible(False)
        self.usage_table.setAlternatingRowColors(True)
        self.usage_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.usage_table)

        self.usage_total = QLabel("Итоговая стоимость продуктов: —")
        self.usage_total.setObjectName("SummaryValue")
        v.addWidget(self.usage_total)
        return w

    def _period(self) -> tuple:
        return (self.date_from.date().toString("yyyy-MM-dd"),
                self.date_to.date().toString("yyyy-MM-dd"))

    def _build_usage(self) -> None:
        date_from, date_to = self._period()
        if date_from > date_to:
            show_warning(self, "Начало периода позже его окончания.")
            return
        self._usage_rows = costing.calc_period_usage(date_from, date_to)
        self.usage_table.setRowCount(len(self._usage_rows))
        total = 0.0
        for r, item in enumerate(self._usage_rows):
            total += item["cost"]
            self.usage_table.setItem(r, 0, cell(item["name"]))
            self.usage_table.setItem(r, 1, cell(item["unit"]))
            self.usage_table.setItem(r, 2, cell(f"{item['required']:g}",
                                                align_right=True))
            self.usage_table.setItem(r, 3, cell(money(item["cost"]),
                                                align_right=True))
        self.usage_total.setText(
            f"Итоговая стоимость продуктов: {money(total)} ₽")
        if not self._usage_rows:
            show_info(self, "За выбранный период банкетов с меню не найдено.")

    def _on_export_usage(self) -> None:
        if not self._usage_rows:
            show_warning(self, "Сначала сформируйте сводку.")
            return
        date_from, date_to = self._period()
        df = pd.DataFrame([{
            "Ингредиент": item["name"],
            "Ед. изм.": item["unit"],
            "Израсходовано": round(item["required"], 3),
            "Стоимость, ₽": round(item["cost"], 2),
        } for item in self._usage_rows])
        path = ask_save_path(self, "Сохранить сводку",
                             "Сводка_по_продуктам.xlsx",
                             "Файлы Excel (*.xlsx)")
        if not path:
            return
        try:
            exporter.export_dataframe_to_excel(
                df, path, sheet_name="Расход продуктов",
                title=f"Сводка по продуктам за период {date_from} — {date_to}")
            log_action("Экспорт сводки по продуктам в Excel")
            show_info(self, f"Сводка сохранена:\n{path}")
        except Exception as exc:
            show_error(self, f"Не удалось сохранить файл: {exc}")

    # ===================================================== НАСТРОЙКИ
    def _build_settings_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        box = QGroupBox("Параметры расчёта и реквизиты")
        form = QFormLayout(box)
        form.setSpacing(10)

        self.overhead_spin = QDoubleSpinBox()
        self.overhead_spin.setRange(0.0, 1000.0)
        self.overhead_spin.setDecimals(1)
        self.overhead_spin.setSuffix(" %")
        self.org_edit = QLineEdit()
        self.city_edit = QLineEdit()
        self.user_edit = QLineEdit()

        form.addRow("Накладные расходы по умолчанию:", self.overhead_spin)
        form.addRow("Организация:", self.org_edit)
        form.addRow("Город:", self.city_edit)
        form.addRow("Текущий пользователь:", self.user_edit)
        v.addWidget(box)

        v.addWidget(make_button("Сохранить настройки", self._save_settings))
        v.addStretch(1)
        return w

    def _load_settings(self) -> None:
        self.overhead_spin.setValue(config.get_overhead_pct())
        self.org_edit.setText(config.get_setting("organization", "ООО «Агнес»"))
        self.city_edit.setText(config.get_setting("city", "Санкт-Петербург"))
        self.user_edit.setText(config.get_current_user())

    def _save_settings(self) -> None:
        user = self.user_edit.text().strip()
        if not user:
            show_warning(self, "Укажите имя текущего пользователя.")
            return
        config.set_setting("overhead_pct", self.overhead_spin.value())
        config.set_setting("organization", self.org_edit.text().strip())
        config.set_setting("city", self.city_edit.text().strip())
        config.set_setting("current_user", user)
        log_action("Изменены настройки приложения")
        show_info(self, "Настройки сохранены.")

    # ===================================================== ЖУРНАЛ ДЕЙСТВИЙ
    def _build_logs_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Последние операции пользователей"))
        toolbar.addStretch(1)
        toolbar.addWidget(make_button("Обновить", self._refresh_logs,
                                      "Secondary"))
        v.addLayout(toolbar)

        self.logs_table = QTableWidget(0, 3)
        self.logs_table.setHorizontalHeaderLabels(
            ["Дата и время", "Пользователь", "Операция"])
        self.logs_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.logs_table.verticalHeader().setVisible(False)
        self.logs_table.setAlternatingRowColors(True)
        header = self.logs_table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.logs_table)
        return w

    def _refresh_logs(self) -> None:
        logs = get_logs()
        self.logs_table.setRowCount(len(logs))
        for r, row in enumerate(logs):
            self.logs_table.setItem(r, 0, cell(row["ts"]))
            self.logs_table.setItem(r, 1, cell(row["username"]))
            self.logs_table.setItem(r, 2, cell(row["operation"]))
        self.logs_table.resizeColumnToContents(0)
        self.logs_table.resizeColumnToContents(1)

    # --------------------------------------------------------- общий refresh
    def refresh(self) -> None:
        self._load_settings()
        self._refresh_logs()
