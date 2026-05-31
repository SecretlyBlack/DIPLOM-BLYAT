"""
Главное окно АРМ банкетного менеджера ООО «Агнес».

Объединяет все функциональные вкладки, оформляет фирменный заголовок-баннер
и строку состояния. При переключении вкладок данные автоматически
обновляются, чтобы изменения в одном разделе сразу отражались в других.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QFrame, QLabel, QTabWidget,
    QStatusBar,
)

from ui import style
from ui.tabs.banquets_tab import BanquetsTab
from ui.tabs.warehouse_tab import WarehouseTab
from ui.tabs.suppliers_tab import SuppliersTab
from ui.tabs.ingredients_tab import IngredientsTab
from ui.tabs.dishes_tab import DishesTab
from ui.tabs.reports_tab import ReportsTab
from core import config


class MainWindow(QMainWindow):
    """Главное окно приложения с вкладками функциональных модулей."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("АРМ банкетного менеджера — ООО «Агнес»")
        self.resize(1180, 760)
        self.setMinimumSize(960, 620)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        # Вкладки функциональных модулей.
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.banquets_tab = BanquetsTab()
        self.warehouse_tab = WarehouseTab()
        self.suppliers_tab = SuppliersTab()
        self.ingredients_tab = IngredientsTab()
        self.dishes_tab = DishesTab()
        self.reports_tab = ReportsTab()

        self.tabs.addTab(self.banquets_tab, "📅  Банкеты")
        self.tabs.addTab(self.warehouse_tab, "📦  Склад и закупки")
        self.tabs.addTab(self.suppliers_tab, "🚚  Поставщики")
        self.tabs.addTab(self.ingredients_tab, "🥕  Ингредиенты")
        self.tabs.addTab(self.dishes_tab, "🍽  Блюда")
        self.tabs.addTab(self.reports_tab, "📊  Отчёты и настройки")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        wrap = QWidget()
        wrap_layout = QVBoxLayout(wrap)
        wrap_layout.setContentsMargins(10, 10, 10, 10)
        wrap_layout.addWidget(self.tabs)
        layout.addWidget(wrap, 1)

        self.setCentralWidget(central)

        # Строка состояния.
        self.setStatusBar(QStatusBar())
        self._update_status()

    def _build_header(self) -> QFrame:
        """Создать верхний баннер с названием АРМ и организации."""
        header = QFrame()
        header.setObjectName("Header")
        v = QVBoxLayout(header)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        title = QLabel("Автоматизированное рабочее место банкетного менеджера")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel(
            f"{config.get_setting('organization', 'ООО «Агнес»')} · "
            f"{config.get_setting('city', 'Санкт-Петербург')}")
        subtitle.setObjectName("HeaderSubtitle")
        v.addWidget(title)
        v.addWidget(subtitle)
        return header

    def _on_tab_changed(self, index: int) -> None:
        """Обновить данные вкладки при её открытии."""
        widget = self.tabs.widget(index)
        if hasattr(widget, "refresh"):
            try:
                widget.refresh()
            except Exception:
                # Сбой обновления не должен закрывать приложение.
                pass
        self._update_status()

    def _update_status(self) -> None:
        """Отобразить текущего пользователя и накладные расходы в статусбаре."""
        self.statusBar().showMessage(
            f"Пользователь: {config.get_current_user()}    |    "
            f"Накладные расходы по умолчанию: {config.get_overhead_pct():.0f}%"
            f"    |    БД: agnes_banquet.db")
