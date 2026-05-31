"""
Базовый класс вкладки-справочника (CRUD).

Содержит общий каркас: панель инструментов с поиском и кнопками
«Добавить / Изменить / Удалить», таблицу данных и стандартную логику
обновления. Конкретные справочники наследуются и переопределяют:

    * ``COLUMNS``       — заголовки колонок таблицы;
    * ``load_rows``     — загрузка строк из репозитория;
    * ``fill_row``      — заполнение строки таблицы данными;
    * ``open_editor``   — открытие диалога добавления/изменения;
    * ``delete_row``    — удаление выбранной записи.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QAbstractItemView,
    QLineEdit, QLabel, QHeaderView,
)

from ui.widgets import make_button, show_warning, confirm


class CrudTab(QWidget):
    """Базовая вкладка с таблицей и операциями создания/изменения/удаления."""

    COLUMNS: list = []          # заголовки колонок (переопределяется)
    SEARCH_PLACEHOLDER = "Поиск…"
    ADD_LABEL = "Добавить"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []          # кэш загруженных записей (sqlite3.Row)
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Панель инструментов.
        toolbar = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.SEARCH_PLACEHOLDER)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.refresh)
        toolbar.addWidget(QLabel("🔍"))
        toolbar.addWidget(self.search_edit, 1)

        toolbar.addWidget(make_button(self.ADD_LABEL, self._on_add))
        toolbar.addWidget(make_button("Изменить", self._on_edit, "Secondary"))
        toolbar.addWidget(make_button("Удалить", self._on_delete, "Danger"))
        layout.addLayout(toolbar)

        # Таблица.
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self.table)

    # -------------------------------------------------------------- helpers
    def current_row(self):
        """Вернуть запись для выделенной строки или ``None``."""
        index = self.table.currentRow()
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    def refresh(self) -> None:
        """Перезагрузить данные таблицы согласно строке поиска."""
        search = self.search_edit.text().strip()
        self._rows = self.load_rows(search)
        self.table.setRowCount(len(self._rows))
        for r, row in enumerate(self._rows):
            self.fill_row(r, row)
        self.table.resizeRowsToContents()

    # ----------------------------------------------------------- callbacks
    def _on_add(self) -> None:
        if self.open_editor(None):
            self.refresh()

    def _on_edit(self, *args) -> None:
        row = self.current_row()
        if row is None:
            show_warning(self, "Выберите запись для изменения.")
            return
        if self.open_editor(row):
            self.refresh()

    def _on_delete(self) -> None:
        row = self.current_row()
        if row is None:
            show_warning(self, "Выберите запись для удаления.")
            return
        if confirm(self, "Удалить выбранную запись? "
                         "Действие необратимо."):
            self.delete_row(row)
            self.refresh()

    # ----------------------------------------------- методы для наследников
    def load_rows(self, search: str) -> list:
        """Загрузить записи (переопределяется в наследнике)."""
        raise NotImplementedError

    def fill_row(self, index: int, row) -> None:
        """Заполнить строку таблицы (переопределяется в наследнике)."""
        raise NotImplementedError

    def open_editor(self, row) -> bool:
        """Открыть диалог добавления/изменения. Вернуть True при сохранении."""
        raise NotImplementedError

    def delete_row(self, row) -> None:
        """Удалить запись (переопределяется в наследнике)."""
        raise NotImplementedError
