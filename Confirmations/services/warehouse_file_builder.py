import pandas as pd
from pathlib import Path
from Common.logger import get_logger

logger = get_logger("Confirmations - WarehouseFileBuilder")


class WarehouseFileBuilder:
    """
    Принимает df с подтверждёнными заказами (OK_df)
    и создаёт Excel-файл с 3 листами:
    1. Сводка по заказам
    2. Сводка товаров для склада по маркам
    3. Полная таблица
    """

    def __init__(self, df: pd.DataFrame, output_path: str):
        self.df = df.copy()
        self.output_path = Path(output_path)

    # ----------------------------------------------------
    #  1. Сводка по заказам
    # ----------------------------------------------------
    def _make_orders_summary(self) -> pd.DataFrame:
        summary = (
            self.df.groupby("ORDER_ID")
            .agg(
                QNT=("QNT", "sum"),
                PRICE_WITH_VAT=("PRICE_WITH_VAT", "sum"),
                DATE_ORDER=("DATE_ORDER", "first"),
                DATE_SHIP=("DATE_SHIP", "first"),
            )
            .reset_index()
        )

        summary.rename(
            columns={
                "ORDER_ID": "Номер заказа",
                "QNT": "Итого позиций",
                "PRICE_WITH_VAT": "Итого с НДС",
                "DATE_ORDER": "Дата заказа",
                "DATE_SHIP": "Дата отгрузки"
            },
            inplace=True,
        )

        return summary

    # ----------------------------------------------------
    #  2. Сводка товаров для склада
    # ----------------------------------------------------
    def _make_items_summary(self) -> pd.DataFrame:
        items = (
            self.df.groupby(["BRAND", "CODEART", "NAME", "DATE_EXPIRATION"])
            .agg(QNT=("QNT", "sum"))
            .reset_index()
        )

        items = items.rename(
            columns={
                "BRAND": "Бренд",
                "CODEART": "Артикул",
                "NAME": "Наименование",
                "DATE_EXPIRATION": "Срок годности",
                "QNT": "Колл-во",
            }
        )
        return items

    # ----------------------------------------------------
    #  3. Полная таблица
    # ----------------------------------------------------
    def _make_full_sheet(self) -> pd.DataFrame:
        df_full = self.df.copy()
        df_full = df_full.rename(columns={
            "ORDER_ID": "Номер заказа",
            "FIRM": "Компания",
            "CODEPST": "Вн. код",
            "CODEART": "Артикул",
            "NAME": "Наименование",
            "QNT": "Количество",
            "PRICE_WITH_VAT": "Цена с НДС",
            "DATE_EXPIRATION": "Срок годности",
            "PODRCD": "Подразделение",
            "DATE_ORDER": "Дата заказа",
            "DATE_SHIP": "Дата отгрузки",
            "REFUSED": "Отказано",
            "BRAND": "Бренд",
        })

        drop_cols = ["Вн. код", "Отказано", "__source_file__", "Подразделение"]

        df_full = df_full.drop(columns=[c for c in drop_cols if c in df_full])

        return df_full

    # ----------------------------------------------------
    #  СОХРАНЕНИЕ EXCEL
    # ----------------------------------------------------
    def save(self):
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            with pd.ExcelWriter(self.output_path, engine="openpyxl") as writer:
                # Лист 1
                orders_summary = self._make_orders_summary()
                orders_summary.to_excel(writer, sheet_name="Orders Summary", index=False)

                # Лист 2
                items_summary = self._make_items_summary()
                items_summary.to_excel(writer, sheet_name="Items by Brand", index=False)

                # Лист 3
                full_sheet = self._make_full_sheet()
                full_sheet.to_excel(writer, sheet_name="Full Data", index=False)

            logger.info(f"Файл для склада создан: {self.output_path}")

        except Exception as e:
            logger.exception(f"Ошибка при формировании Excel: {e}")
            raise
