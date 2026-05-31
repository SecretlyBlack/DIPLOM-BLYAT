"""
Оформление приложения (QSS-стили).

Фирменная палитра: синий (#2F5597), белый (#FFFFFF), серый (#F0F2F5).
Стиль задаёт единый вид для кнопок, таблиц, вкладок, полей ввода и заголовков.
"""

# Основные цвета вынесены в константы для повторного использования в коде.
PRIMARY = "#2F5597"      # основной синий
PRIMARY_DARK = "#1F3864"  # тёмно-синий (наведение)
BG = "#F0F2F5"           # фон окна (светло-серый)
WHITE = "#FFFFFF"
TEXT = "#222222"

# Цвета индикации складских остатков.
COLOR_OK = "#2E7D32"        # норма (зелёный)
COLOR_WARNING = "#F9A825"   # близко к минимуму (жёлтый)
COLOR_CRITICAL = "#C62828"  # критично (красный)

APP_QSS = f"""
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

/* Заголовок-баннер вверху окна */
QFrame#Header {{
    background-color: {PRIMARY};
    border: none;
}}
QLabel#HeaderTitle {{
    color: {WHITE};
    font-size: 18px;
    font-weight: bold;
    padding: 10px 16px;
}}
QLabel#HeaderSubtitle {{
    color: #D6E0F5;
    font-size: 12px;
    padding: 0 16px 8px 16px;
}}

/* Вкладки */
QTabWidget::pane {{
    border: 1px solid #C9D2E0;
    background: {WHITE};
    border-radius: 6px;
}}
QTabBar::tab {{
    background: #DCE3EF;
    color: {PRIMARY_DARK};
    padding: 9px 18px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background: {WHITE};
    color: {PRIMARY};
    border-bottom: 3px solid {PRIMARY};
}}
QTabBar::tab:hover {{
    background: #E8EDF6;
}}

/* Кнопки */
QPushButton {{
    background-color: {PRIMARY};
    color: {WHITE};
    border: none;
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {PRIMARY_DARK};
}}
QPushButton:pressed {{
    background-color: #16294a;
}}
QPushButton:disabled {{
    background-color: #A9B4C7;
    color: #EDEFF3;
}}
QPushButton#Secondary {{
    background-color: {WHITE};
    color: {PRIMARY};
    border: 1px solid {PRIMARY};
}}
QPushButton#Secondary:hover {{
    background-color: #E8EDF6;
}}
QPushButton#Danger {{
    background-color: {COLOR_CRITICAL};
}}
QPushButton#Danger:hover {{
    background-color: #8E1B1B;
}}

/* Таблицы */
QTableWidget, QTableView {{
    background: {WHITE};
    gridline-color: #E1E6EF;
    selection-background-color: #D6E0F5;
    selection-color: {TEXT};
    border: 1px solid #C9D2E0;
    border-radius: 6px;
}}
QHeaderView::section {{
    background-color: {PRIMARY};
    color: {WHITE};
    padding: 6px;
    border: none;
    font-weight: 600;
}}
QTableWidget::item {{
    padding: 4px;
}}

/* Поля ввода */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QTextEdit {{
    background: {WHITE};
    border: 1px solid #C9D2E0;
    border-radius: 4px;
    padding: 5px 7px;
    selection-background-color: {PRIMARY};
    selection-color: {WHITE};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateEdit:focus, QTimeEdit:focus, QTextEdit:focus {{
    border: 1px solid {PRIMARY};
}}

/* Группы */
QGroupBox {{
    border: 1px solid #C9D2E0;
    border-radius: 6px;
    margin-top: 14px;
    background: {WHITE};
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {PRIMARY};
}}

/* Строка состояния */
QStatusBar {{
    background: {PRIMARY_DARK};
    color: {WHITE};
}}

QLabel#SummaryValue {{
    font-size: 15px;
    font-weight: bold;
    color: {PRIMARY_DARK};
}}
"""
