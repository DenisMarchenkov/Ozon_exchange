from typing import Iterable

import pandas as pd
from pathlib import Path
from Common.logger import get_logger

logger = get_logger("Confirmations - WarehouseFileBuilder")


class WarehouseFileBuilder:
    """
    Формирует Excel-файл для склада.

    Принимает:
        rows: list[dict] — данные (обычно из БД)
    """

    def __init__(self, rows: Iterable[dict], output_path: str | Path):
        self.rows = list(rows)
        self.output_path = Path(output_path)

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
            "date_order",
            "date_ship",
        ]
        self._check_required(required_cols, "Orders Summary")

        summary = (
            self.df.groupby("posting_number")
            .agg(
                QNT=("quantity_confirm", "sum"),
                PRICE_WITH_VAT=("price_with_vat", "sum"),
                DATE_ORDER=("date_order", "first"),
                DATE_SHIP=("date_ship", "first"),
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

        items = (
            self.df.groupby(
                ["brand", "sku_art", "name", "date_expiration"]
            )
            .agg(QNT=("quantity_confirm", "sum"))
            .reset_index()
        )

        items.rename(
            columns={
                "brand": "Бренд",
                "sku_art": "Артикул",
                "name": "Наименование",
                "date_expiration": "Срок годности",
                "QNT": "Колл-во",
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
            "quantity_confirm": "Количество",
            "price_with_vat": "Цена с НДС",
            "date_expiration": "Срок годности",
            "date_order": "Дата заказа",
            "date_ship": "Дата отгрузки",
        }

        df_full = self.df.rename(columns=rename_map)

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
    def save(self):
        try:
            # 👉 СНАЧАЛА строим все листы
            orders = self._make_orders_summary()
            items = self._make_items_summary()
            full = self._make_full_sheet()

            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            with pd.ExcelWriter(self.output_path, engine="openpyxl") as writer:
                orders.to_excel(writer, sheet_name="Orders Summary", index=False)
                items.to_excel(writer, sheet_name="Items by Brand", index=False)
                full.to_excel(writer, sheet_name="Full Data", index=False)

            logger.info(f"Файл для склада создан: {self.output_path}")

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