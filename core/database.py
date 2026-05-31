"""
Модуль работы с базой данных SQLite.

Содержит:
    * единую точку подключения к файлу agnes_banquet.db;
    * создание схемы (таблиц справочников, банкетов, склада, закупок, логов);
    * вспомогательные функции выполнения запросов с обработкой исключений.

Соединение возвращает строки в виде sqlite3.Row, что позволяет
обращаться к полям по имени (row["name"]).
"""

import os
import sqlite3
from contextlib import contextmanager

# Имя файла базы данных согласно техническому заданию.
DB_FILENAME = "agnes_banquet.db"

# Полный путь к файлу БД (рядом с корнем проекта).
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, DB_FILENAME)


def get_connection() -> sqlite3.Connection:
    """Создать и вернуть новое подключение к базе данных.

    Включается поддержка внешних ключей (по умолчанию в SQLite отключена)
    и режим row_factory для доступа к колонкам по имени.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_cursor(commit: bool = False):
    """Контекстный менеджер курсора БД.

    :param commit: выполнять ли commit после успешного блока.

    Гарантирует закрытие соединения и откат транзакции при исключении.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        if commit:
            conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# DDL — определение структуры базы данных
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- Справочник поставщиков
CREATE TABLE IF NOT EXISTS suppliers (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL UNIQUE,
    inn            TEXT,
    phone          TEXT,
    email          TEXT,
    contact_person TEXT,
    city           TEXT,
    rating         REAL    DEFAULT 0       -- рейтинг поставщика, 0..5
);

-- Справочник ингредиентов (складские позиции)
CREATE TABLE IF NOT EXISTS ingredients (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL UNIQUE,
    unit           TEXT    NOT NULL,        -- единица измерения (кг, л, шт)
    purchase_price REAL    NOT NULL DEFAULT 0,  -- закупочная цена за единицу
    stock          REAL    NOT NULL DEFAULT 0,  -- текущий остаток
    min_stock      REAL    NOT NULL DEFAULT 0,  -- минимальный запас
    supplier_id    INTEGER,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id) ON DELETE SET NULL
);

-- Справочник блюд
CREATE TABLE IF NOT EXISTS dishes (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT    NOT NULL UNIQUE,
    category TEXT
);

-- Норма расхода ингредиентов на 1 порцию блюда
CREATE TABLE IF NOT EXISTS dish_ingredients (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_id       INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    norm          REAL    NOT NULL DEFAULT 0,   -- расход на 1 порцию
    UNIQUE (dish_id, ingredient_id),
    FOREIGN KEY (dish_id)       REFERENCES dishes (id)      ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients (id) ON DELETE CASCADE
);

-- Банкеты (заявки на обслуживание).
-- Зал у ООО «Агнес» один и собственный, поэтому аренда и выбор зала
-- не учитываются.
CREATE TABLE IF NOT EXISTS banquets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name  TEXT    NOT NULL,
    event_date   TEXT    NOT NULL,           -- дата проведения (ГГГГ-ММ-ДД)
    event_time   TEXT,                       -- время проведения (ЧЧ:ММ)
    guests       INTEGER NOT NULL DEFAULT 0,
    overhead_pct REAL    NOT NULL DEFAULT 0, -- % накладных расходов на момент создания
    status       TEXT    NOT NULL DEFAULT 'Новая',
    comment      TEXT,
    created_at   TEXT    NOT NULL
);

-- Состав меню банкета (выбранные блюда и число порций)
CREATE TABLE IF NOT EXISTS banquet_dishes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    banquet_id INTEGER NOT NULL,
    dish_id    INTEGER NOT NULL,
    portions   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (banquet_id, dish_id),
    FOREIGN KEY (banquet_id) REFERENCES banquets (id) ON DELETE CASCADE,
    FOREIGN KEY (dish_id)    REFERENCES dishes (id)   ON DELETE CASCADE
);

-- Журнал закупок (заявки поставщикам)
CREATE TABLE IF NOT EXISTS purchases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER,
    status      TEXT    NOT NULL DEFAULT 'Создана',
    created_at  TEXT    NOT NULL,
    comment     TEXT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers (id) ON DELETE SET NULL
);

-- Позиции заявки на закупку
CREATE TABLE IF NOT EXISTS purchase_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id   INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    qty           REAL    NOT NULL DEFAULT 0,
    price         REAL    NOT NULL DEFAULT 0,
    FOREIGN KEY (purchase_id)   REFERENCES purchases (id)   ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients (id) ON DELETE CASCADE
);

-- Настройки приложения (ключ-значение)
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Журнал действий пользователя
CREATE TABLE IF NOT EXISTS logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,        -- дата и время (ГГГГ-ММ-ДД ЧЧ:ММ:СС)
    username  TEXT NOT NULL,
    operation TEXT NOT NULL
);
"""


def init_db() -> None:
    """Создать структуру базы данных, если она ещё не создана."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
