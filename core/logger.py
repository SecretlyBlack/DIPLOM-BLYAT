"""
Модуль логирования действий пользователя.

Каждое значимое действие (создание, изменение, удаление, экспорт, смена статуса)
фиксируется в таблице ``logs`` с указанием даты, пользователя и описания операции.
"""

from datetime import datetime

from core.database import db_cursor
from core import config


def log_action(operation: str, username: str | None = None) -> None:
    """Записать действие в журнал.

    :param operation: текстовое описание операции.
    :param username:  имя пользователя; если не указано — берётся из настроек.
    """
    if username is None:
        username = config.get_current_user()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO logs (ts, username, operation) VALUES (?, ?, ?)",
                (ts, username, operation),
            )
    except Exception:
        # Логирование не должно прерывать основную работу приложения.
        pass


def get_logs(limit: int = 500) -> list:
    """Вернуть последние записи журнала (по убыванию даты)."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT ts, username, operation FROM logs "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()
