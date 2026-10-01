import sqlite3
import sys

sys.path.append(r"C:\Users\dmarc\PycharmProjects\Ozon_exchange")
from Common.settings import DB_PATH


def add_column(
    table_name: str,
    column_name: str,
    column_type: str,
    default=None,
) -> bool:
    """
    Добавляет столбец в таблицу, если его ещё нет.

    :param table_name: название таблицы
    :param column_name: название нового столбца
    :param column_type: тип столбца
    :param default: значение по умолчанию
    :return: True, если столбец был добавлен
    """

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            # Проверяем существование таблицы
            cur.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = ?
                """,
                (table_name,),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    f"Table '{table_name}' does not exist."
                )

            # Получаем существующие столбцы
            cur.execute(f'PRAGMA table_info("{table_name}")')
            columns = {row[1] for row in cur.fetchall()}

            if column_name in columns:
                print(
                    f"Column '{column_name}' "
                    f"already exists in '{table_name}'."
                )
                return False

            # Формируем DEFAULT
            default_sql = ""

            if default is not None:
                if isinstance(default, str):
                    default_sql = f" DEFAULT '{default}'"
                elif isinstance(default, bool):
                    default_sql = f" DEFAULT {int(default)}"
                else:
                    default_sql = f" DEFAULT {default}"

            # Добавляем столбец
            cur.execute(
                f'ALTER TABLE "{table_name}" '
                f'ADD COLUMN "{column_name}" '
                f'{column_type}{default_sql}'
            )

            print(
                f"Column '{column_name}' "
                f"added to '{table_name}' "
                f"with default={default!r}."
            )

            return True

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    add_column(
        table_name="orders",
        column_name="scanit",
        column_type="TEXT",
        default="",
    )