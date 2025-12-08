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
            self.df.groupby("HDRTAG2")
            .agg(
                QNT=("QNT", "sum"),
                PRICE2=("PRICE2", "sum"),
                DATEZ=("DATEZ", "first"),
                HDRTAG1=("HDRTAG1", "first"),
            )
            .reset_index()
        )

        summary.rename(
            columns={
                "HDRTAG2": "ORDER_ID",
                "QNT": "TOTAL_QNT",
                "PRICE2": "TOTAL_SUM",
            },
            inplace=True,
        )

        return summary

    # ----------------------------------------------------
    #  2. Сводка товаров для склада
    # ----------------------------------------------------
    def _make_items_summary(self) -> pd.DataFrame:
        items = (
            self.df.groupby(["FIRM", "CODEART", "NAME", "GDATE"])
            .agg(QNT=("QNT", "sum"))
            .reset_index()
        )
        return items

    # ----------------------------------------------------
    #  3. Полная таблица
    # ----------------------------------------------------
    def _make_full_sheet(self) -> pd.DataFrame:
        return self.df.copy()

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
                items_summary.to_excel(writer, sheet_name="Items by FIRM", index=False)

                # Лист 3
                full_sheet = self._make_full_sheet()
                full_sheet.to_excel(writer, sheet_name="Full Data", index=False)

            logger.info(f"Файл для склада создан: {self.output_path}")

        except Exception as e:
            logger.exception(f"Ошибка при формировании Excel: {e}")
            raise
