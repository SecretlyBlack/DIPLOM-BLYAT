"""
АРМ банкетного менеджера ООО «Агнес» (Санкт-Петербург).

Точка входа в приложение. Выполняет инициализацию базы данных и настроек,
наполнение демонстрационными данными (при первом запуске), применяет
оформление и открывает главное окно.

Запуск:
    python main.py
"""

import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox

from core.database import init_db
from core.config import init_settings
from core.seed import seed_data
from core.logger import log_action
from ui.style import APP_QSS
from ui.main_window import MainWindow


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    """Глобальный обработчик необработанных исключений GUI.

    Показывает пользователю понятное сообщение вместо аварийного завершения.
    """
    message = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    sys.stderr.write(message)
    QMessageBox.critical(
        None, "Непредвиденная ошибка",
        "В приложении произошла ошибка:\n\n"
        f"{exc_value}\n\nПодробности выведены в консоль.")


def main() -> int:
    """Инициализировать систему и запустить графический интерфейс."""
    # Подготовка базы данных и настроек до создания окон.
    init_db()
    init_settings()
    seed_data()

    app = QApplication(sys.argv)
    app.setApplicationName("АРМ банкетного менеджера «Агнес»")
    app.setStyleSheet(APP_QSS)

    sys.excepthook = _excepthook

    window = MainWindow()
    window.show()
    log_action("Запуск приложения")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
