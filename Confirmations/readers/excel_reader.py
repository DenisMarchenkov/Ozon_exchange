from pprint import pprint

import pandas as pd
from pathlib import Path
import shutil

from Common.logger import get_logger
from Common.settings import CONFIRMATIONS_DIR

logger = get_logger("Confirmations")


class ConfirmationsReader:
    REQUIRED_COLUMNS = ['HDRTAG2', 'FIRM', 'CODEPST', 'CODEART', 'NAME', 'QNT', 'PRICE2', 'GDATE', 'PODRCD', 'DATEZ', 'HDRTAG1', 'REFUSED']   # обязательные столбцы
    OPTIONAL_COLUMNS = []                       # можно расширять, не обязательны

    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)

        self.df_all = None
        self.ok_df = None
        self.bad_df = None

        self.ok_folder = self.folder_path / "processed" / "OK"
        self.bad_folder = self.folder_path / "processed" / "BAD"

        logger.info(f"Чтение файлов подтверждений из папки: {self.folder_path}")

        self._load_all_files()
        self._split_good_bad()
        self._move_processed_files()

    # -----------------------------
    #   ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
    # -----------------------------

    def _extract_order_number_from_filename(self, filename: str) -> str:
        return Path(filename).stem  # '123456.xlsx' → '123456'

    def _validate_columns(self, df, filename):
        """Проверяет обязательные колонки, логирует отсутствующие."""
        columns = df.columns.tolist()

        missing_required = [c for c in self.REQUIRED_COLUMNS if c not in columns]
        if missing_required:
            raise ValueError(
                f"Файл {filename} не содержит обязательные колонки: {missing_required}"
            )

        extra_columns = [c for c in columns if c not in self.REQUIRED_COLUMNS]
        if extra_columns:
            logger.info(f"Файл {filename} содержит новые колонки: {extra_columns}")

    # -----------------------------
    #   ЗАГРУЗКА ВСЕХ ФАЙЛОВ
    # -----------------------------

    def _load_all_files(self):
        files = list(self.folder_path.glob("*.xls"))

        if not files:
            logger.warning("Нет Excel файлов подтверждений.")
            self.df_all = pd.DataFrame()
            return

        frames = []

        for file in files:
            try:
                df = pd.read_excel(file)

                # Проверка столбцов
                self._validate_columns(df, file.name)

                # Проверка номера заказа
                order_from_file = self._extract_order_number_from_filename(file.name)
                unique_orders = df["HDRTAG2"].astype(str).unique()

                if len(unique_orders) != 1:
                    logger.warning(
                        f"Файл {file.name}: в HDRTAG2 более одного номера заказа → {unique_orders}"
                    )

                order_from_column = str(unique_orders[0])

                if order_from_file != order_from_column:
                    logger.warning(
                        f"Файл {file.name}: несоответствие имени файла ({order_from_file}) "
                        f"и HDRTAG2 ({order_from_column})"
                    )

                # добавим унифицированный номер заказа
                df["ORDER_ID"] = order_from_column
                df["__source_file__"] = file.name

                frames.append(df)
                logger.info(f"Загружен файл: {file.name} (строк: {len(df)})")

            except Exception as e:
                logger.error(f"Ошибка в файле {file.name}: {e}")

        self.df_all = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # -----------------------------
    #    РАЗДЕЛЕНИЕ НА OK/BAD
    # -----------------------------

    def _split_good_bad(self):
        if self.df_all.empty:
            self.ok_df = pd.DataFrame()
            self.bad_df = pd.DataFrame()
            return

        self.df_all["REFUSED"] = pd.to_numeric(
            self.df_all["REFUSED"], errors="coerce"
        ).fillna(0)

        # какие заказы имеют отказ?
        has_refused = self.df_all.groupby("ORDER_ID")["REFUSED"].apply(
            lambda x: (x > 0).any()
        )

        bad_orders = has_refused[has_refused].index
        good_orders = has_refused[~has_refused].index

        self.bad_df = self.df_all[self.df_all["ORDER_ID"].isin(bad_orders)].copy()
        self.ok_df = self.df_all[self.df_all["ORDER_ID"].isin(good_orders)].copy()

    # -----------------------------
    #    ПЕРЕМЕЩЕНИЕ ФАЙЛОВ
    # -----------------------------

    def _move_processed_files(self):
        """Перемещает файлы в processed/OK и processed/BAD."""

        self.ok_folder.mkdir(parents=True, exist_ok=True)
        self.bad_folder.mkdir(parents=True, exist_ok=True)

        if self.df_all.empty:
            return

        for filename in self.df_all["__source_file__"].unique():
            order_id = self._extract_order_number_from_filename(filename)
            src = self.folder_path / filename

            # if src.exists():
            #     if order_id in self.ok_df["ORDER_ID"].unique():
            #         dst = self.ok_folder / filename
            #     else:
            #         dst = self.bad_folder / filename
            #
            #     try:
            #         shutil.move(str(src), str(dst))
            #         logger.info(f"Файл {filename} перемещён в {dst}")
            #     except Exception as e:
            #         logger.error(f"Не удалось переместить {filename}: {e}")


