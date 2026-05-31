"""
Модуль настроек приложения.

Настройки хранятся в таблице ``settings`` базы данных в виде пар «ключ-значение».
Здесь же заданы значения по умолчанию и удобные геттеры/сеттеры с приведением типов.
"""

from core.database import db_cursor

# Ключи настроек и их значения по умолчанию.
DEFAULTS = {
    "overhead_pct": "20",          # процент накладных расходов
    "organization": 'ООО «Агнес»',  # наименование организации
    "city": "Санкт-Петербург",     # город
    "current_user": "Менеджер",    # текущий пользователь (для журнала)
}


def init_settings() -> None:
    """Записать значения по умолчанию, если соответствующих ключей ещё нет."""
    with db_cursor(commit=True) as cur:
        for key, value in DEFAULTS.items():
            cur.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )


def get_setting(key: str, default: str = "") -> str:
    """Вернуть строковое значение настройки по ключу."""
    with db_cursor() as cur:
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
    if row is not None:
        return row["value"]
    return DEFAULTS.get(key, default)


def set_setting(key: str, value: str) -> None:
    """Установить (создать или обновить) значение настройки."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def get_overhead_pct() -> float:
    """Вернуть процент накладных расходов в виде числа (с защитой от ошибок)."""
    try:
        return float(get_setting("overhead_pct", "20"))
    except (TypeError, ValueError):
        return 20.0


def get_current_user() -> str:
    """Вернуть имя текущего пользователя для журнала действий."""
    return get_setting("current_user", "Менеджер")
