"""
Вспомогательные функции и компоненты графического интерфейса.

Содержит унифицированные диалоги сообщений, фабрики кнопок и утилиты
заполнения таблиц — чтобы не дублировать код во вкладках.
"""

from PyQt6.QtWidgets import (
    QMessageBox, QPushButton, QTableWidgetItem, QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


def show_error(parent, text: str, title: str = "Ошибка") -> None:
    """Показать модальное окно с сообщением об ошибке."""
    QMessageBox.critical(parent, title, text)


def show_info(parent, text: str, title: str = "Информация") -> None:
    """Показать информационное окно."""
    QMessageBox.information(parent, title, text)


def show_warning(parent, text: str, title: str = "Внимание") -> None:
    """Показать предупреждение."""
    QMessageBox.warning(parent, title, text)


def confirm(parent, text: str, title: str = "Подтверждение") -> bool:
    """Запросить подтверждение действия (Да/Нет). Возвращает True при «Да»."""
    reply = QMessageBox.question(
        parent, title, text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


def make_button(text: str, slot=None, object_name: str = "") -> QPushButton:
    """Создать кнопку с подключённым обработчиком и стилевым именем."""
    btn = QPushButton(text)
    if object_name:
        btn.setObjectName(object_name)
    if slot is not None:
        btn.clicked.connect(slot)
    return btn


def cell(text, align_right: bool = False, color: QColor | None = None,
         bold: bool = False) -> QTableWidgetItem:
    """Создать ячейку таблицы (только для чтения) с форматированием."""
    item = QTableWidgetItem("" if text is None else str(text))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if align_right:
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
    if color is not None:
        item.setForeground(color)
    if bold:
        font = item.font()
        font.setBold(True)
        item.setFont(font)
    return item


def money(value) -> str:
    """Отформатировать число как денежную сумму (разделители разрядов)."""
    try:
        return f"{float(value):,.2f}".replace(",", " ")
    except (TypeError, ValueError):
        return "0,00"


def ask_save_path(parent, caption: str, default_name: str,
                  file_filter: str) -> str:
    """Открыть диалог сохранения файла и вернуть выбранный путь (или '')."""
    path, _ = QFileDialog.getSaveFileName(
        parent, caption, default_name, file_filter
    )
    return path
