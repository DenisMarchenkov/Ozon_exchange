import pandas as pd
import hashlib
from pathlib import Path
from typing import Iterable, Optional

def extract_excel_metadata(
    file_path: str | Path,
    columns_for_hash: Iterable[str],
    sort_by: Optional[str | list[str]] = None,
    sheet_name: int | str = 0,
) -> dict:
    """
    Извлекает метаданные Excel-файла и считает хеш по выбранным колонкам.

    :param file_path: путь к файлу xls/xlsx
    :param columns_for_hash: список колонок для хеша
    :param sort_by: колонка или список колонок для стабильной сортировки
    :param sheet_name: лист Excel (по умолчанию первый)
    :return: словарь с метаданными
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    # читаем Excel
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # проверка колонок для хеша
    missing = set(columns_for_hash) - set(df.columns)
    if missing:
        raise ValueError(f"В файле нет колонок: {missing}")

    # хеш по выбранным колонкам
    df_hash = df[list(columns_for_hash)].fillna("").astype(str)
    if sort_by:
        df_hash = df_hash.sort_values(by=sort_by)
    data_string = "|".join(df_hash.values.flatten())
    file_hash = hashlib.sha256(data_string.encode("utf-8")).hexdigest()

    # метаданные
    metadata = {
        "name": file_path.name,
        "file_hash": file_hash,
        "file_size": file_path.stat().st_size,
        "row_count": len(df),
        "columns": ",".join(df.columns),
        "total_qty": int(df["Количество"].sum()) if "Количество" in df.columns else None,
    }

    return metadata