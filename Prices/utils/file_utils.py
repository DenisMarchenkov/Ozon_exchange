import pandas as pd
import hashlib
from pathlib import Path


def extract_excel_metadata_per_sheet(
    file_path: str | Path,
    sheets_info: list[dict],  # [{"sheet_name": 0, "columns_for_hash": [...], "sort_by": [...]}, ...]
) -> dict:
    """
    Считает метаданные Excel-файла по каждому листу отдельно.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    result = {
        "name": file_path.name,
        "file_size": file_path.stat().st_size,
        "sheets": [],
        "row_count": 0,
        "columns": [],
        "total_qty": 0
    }

    schema_info = []
    total_qty_sum = 0
    has_qty_column = False
    
    for sheet in sheets_info:
        sheet_name = sheet["sheet_name"]
        columns_for_hash = sheet["columns_for_hash"]
        sort_by = sheet.get("sort_by")

        df = pd.read_excel(file_path, sheet_name=sheet_name)

        missing = set(columns_for_hash) - set(df.columns)
        if missing:
            raise ValueError(f"Лист '{sheet_name}': нет колонок {missing}")

        df_hash = df[columns_for_hash].fillna("").astype(str)
        if sort_by:
            df_hash = df_hash.sort_values(by=sort_by)

        data_string = "|".join(df_hash.values.flatten())
        file_hash = hashlib.sha256(data_string.encode("utf-8")).hexdigest()

        total_qty = int(df["Количество"].sum()) if "Количество" in df.columns else None
        if total_qty is not None:
            total_qty_sum += total_qty
            has_qty_column = True

        result["sheets"].append({
            "sheet_name": sheet_name,
            "file_hash": file_hash,
            "row_count": len(df),
            "columns": ",".join(df.columns),
            "total_qty": total_qty,
        })
        
        result["row_count"] += len(df)

        schema_info.append(f"{sheet_name}({len(df)}x{len(df.columns)})")

    # Вычисляем комбинированный хеш по всем листам
    combined_hash_str = "|".join(s["file_hash"] for s in result["sheets"])
    result["file_hash"] = hashlib.sha256(combined_hash_str.encode("utf-8")).hexdigest()
    result["columns"] = "; ".join(schema_info)
    result["total_qty"] = total_qty_sum if has_qty_column else None

    return result