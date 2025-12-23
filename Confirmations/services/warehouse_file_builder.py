from datetime import datetime
from typing import Iterable

import pandas as pd
from pathlib import Path
from Common.logger import get_logger
from Confirmations.settings_app.settings_confirmations import ARCHIVE_DIR_WAREHOUSE

from openpyxl import load_workbook
from Confirmations.services.warehouse_file_formater import WarehouseExcelFormatter

logger = get_logger(__name__)


class WarehouseFileBuilder:
    """
    Формирует Excel-файл для склада.

    Принимает:
        rows: list[dict] — данные (обычно из БД)
    """

    def __init__(self, rows: Iterable[dict], suffix = None):
        self.rows = list(rows)
        self.suffix = suffix or "default"
        #self.output_path = Path(output_path)

        if not self.rows:
            logger.warning("WarehouseFileBuilder получил пустые данные")

        # DataFrame — внутренний инструмент
        self.df = pd.DataFrame(self.rows)


    # ----------------------------------------------------
    #  1. Сводка по заказам
    # ----------------------------------------------------
    def _make_orders_summary(self) -> pd.DataFrame:
        required_cols = [
            "posting_number",
            "quantity_confirm",
            "price_with_vat",
            "ordered_at",
            "shipped_at",
        ]
        self._check_required(required_cols, "Orders Summary")

        df_summary = self.df.copy()

        # ВАЖНО: приводим к дате без времени
        df_summary["ordered_at"] = pd.to_datetime(df_summary["ordered_at"], errors="coerce").dt.date
        df_summary["shipped_at"] = pd.to_datetime(df_summary["shipped_at"], errors="coerce").dt.date

        summary = (
            df_summary.groupby("posting_number")
            .agg(
                QNT=("quantity_confirm", "sum"),
                PRICE_WITH_VAT=("price_with_vat", "sum"),
                DATE_ORDER=("ordered_at", "first"),
                DATE_SHIP=("shipped_at", "first"),
            )
            .reset_index()
        )

        summary.rename(
            columns={
                "posting_number": "Номер заказа",
                "QNT": "Итого позиций",
                "PRICE_WITH_VAT": "Итого с НДС",
                "DATE_ORDER": "Дата заказа",
                "DATE_SHIP": "Дата отгрузки",
            },
            inplace=True,
        )

        return summary

    # ----------------------------------------------------
    #  2. Сводка товаров для склада
    # ----------------------------------------------------
    def _make_items_summary(self) -> pd.DataFrame:
        required_cols = [
            "brand",
            "sku_art",
            "name",
            "date_expiration",
            "quantity_confirm",
        ]
        self._check_required(required_cols, "Items Summary")

        df_items = self.df.copy()

        # ВАЖНО: приводим к дате без времени
        df_items["date_expiration"] = (pd.to_datetime(df_items["date_expiration"], errors="coerce")
                                       .dt.date)

        items = (
            df_items.groupby(["brand", "sku_art", "name", "date_expiration"])
            .agg(QNT=("quantity_confirm", "sum"))
            .reset_index()
        )

        items.rename(
            columns={
                "brand": "Бренд",
                "sku_art": "Артикул",
                "name": "Наименование",
                "date_expiration": "Срок годности",
                "QNT": "Кол-во",
            },
            inplace=True,
        )

        return items

    # ----------------------------------------------------
    #  3. Полная таблица
    # ----------------------------------------------------
    def _make_full_sheet(self) -> pd.DataFrame:
        rename_map = {
            "posting_number": "Номер заказа",
            "brand": "Бренд",
            "sku_art": "Артикул",
            "name": "Наименование",
            "quantity_confirm": "Кол-во",
            "date_expiration": "Срок годности",
        }

        df_full = self.df.rename(columns=rename_map)

        # ВАЖНО: приводим к дате без времени
        df_full["Срок годности"] = (
            pd.to_datetime(df_full["Срок годности"], errors="coerce")
            .dt.date
        )

        keep_cols = list(rename_map.values())

        existing = [c for c in keep_cols if c in df_full.columns]
        missing = [c for c in keep_cols if c not in df_full.columns]

        if missing:
            logger.warning(
                f"В выходном файле отсутствуют ожидаемые колонки: {missing}"
            )

        return df_full[existing]

    # ----------------------------------------------------
    #  Сохранение Excel
    # ----------------------------------------------------
    def build(self) -> Path:
        try:
            orders = self._make_orders_summary()
            items = self._make_items_summary()
            full = self._make_full_sheet()

            file_path = self._build_filename()

            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                orders.to_excel(writer, sheet_name="Orders Summary", index=False)
                items.to_excel(writer, sheet_name="Items by Brand", index=False)
                full.to_excel(writer, sheet_name="Full Data", index=False)

            logger.info(f"Файл для склада создан: {file_path}")

            # запускаем форматирование файла
            formatter = WarehouseExcelFormatter(str(file_path))
            wb = load_workbook(file_path)

            # TODO суффикс - название магазина, вынести в настройки
            formatter.apply_common(wb["Orders Summary"], "ORDERS")
            formatter.format_orders_summary(wb["Orders Summary"])

            formatter.apply_common(wb["Items by Brand"], "ITEMS")
            formatter.format_items_summary(wb["Items by Brand"])

            formatter.apply_common(wb["Full Data"], "FULL")
            formatter.format_full_data(wb["Full Data"])
            wb.save(file_path)

            return file_path

        except Exception:
            logger.exception("Ошибка при формировании Excel-файла")
            raise

    # ----------------------------------------------------
    #  Валидация
    # ----------------------------------------------------
    def _check_required(self, cols: list[str], sheet_name: str):
        missing = [c for c in cols if c not in self.df.columns]
        if missing:
            raise ValueError(
                f"Недостаточно данных для листа '{sheet_name}'. "
                f"Отсутствуют колонки: {missing}"
            )

    #@staticmethod
    def _build_filename(self) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        name = f"warehouse_file__{timestamp}_{self.suffix}.xlsx"
        return Path(ARCHIVE_DIR_WAREHOUSE) / name
