import json
import os

import pandas as pd
from pathlib import Path
import shutil

from Common.logger import get_logger
from Common.settings import COMMON_DIR, BASE_DIR

logger = get_logger("Confirmations")


class ConfirmationsReader:

    def __init__(self, folder_path: str, mapping_file: str = None):
        """
        :param folder_path: путь к папке с Excel файлами
        :param mapping_file: путь к column_map.json; если None — ищем в Common/config/
        """
        self.folder_path = Path(folder_path)

        # путь к файлу маппинга
        if mapping_file is None:
            mapping_file = os.path.join(BASE_DIR, "Confirmations","column_map.json")

        # загрузка маппинга
        with open(mapping_file, "r", encoding="utf-8") as f:
            self.COLUMN_MAP = json.load(f)

        self.REQUIRED_COLUMNS = list(self.COLUMN_MAP.keys())

        # таблицы
        self.df_all = None
        self.ok_df = None
        self.bad_df = None

        # папки назначения
        self.ok_folder = self.folder_path / "processed" / "OK"
        self.bad_folder = self.folder_path / "processed" / "BAD"

        logger.info(f"Чтение файлов подтверждений из папки: {self.folder_path}")

        # пайплайн
        self._load_all_files()
        self._split_good_bad()
        self._move_processed_files()

    # -------------------------------------------------------------
    #   МАППИНГ И НОРМАЛИЗАЦИЯ
    # -------------------------------------------------------------
    def _normalize_columns(self, df: pd.DataFrame, filename: str) -> pd.DataFrame:
        """
        Приводит имена колонок к внутреннему стандарту согласно COLUMN_MAP.
        """
        new_names = {}

        for standard_name, possible_names in self.COLUMN_MAP.items():
            for col in possible_names:
                if col in df.columns:
                    new_names[col] = standard_name
                    break

        # какие обязательные не найдены?
        missing = [col for col in self.REQUIRED_COLUMNS if col not in new_names.values()]
        if missing:
            raise ValueError(
                f"Файл {filename} не содержит обязательные колонки после нормализации: {missing}"
            )

        df = df.rename(columns=new_names)
        return df

    # -------------------------------------------------------------
    #   ЗАГРУЗКА ВСЕХ ФАЙЛОВ
    # -------------------------------------------------------------
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

                # Нормализация колонок
                df = self._normalize_columns(df, file.name)

                # Проверка номера заказа
                order_from_file = self._extract_order_number_from_filename(file.name)
                unique_orders = df["ORDER_ID"].astype(str).unique()

                if len(unique_orders) != 1:
                    logger.warning(
                        f"Файл {file.name}: в ORDER_ID более одного номера заказа → {unique_orders}"
                    )

                order_from_column = str(unique_orders[0])

                if order_from_file != order_from_column:
                    logger.warning(
                        f"Файл {file.name}: несоответствие имени файла ({order_from_file}) "
                        f"и ORDER_ID ({order_from_column})"
                    )

                # добавим единый ORDER_ID
                df["ORDER_ID"] = order_from_column
                df["__source_file__"] = file.name

                frames.append(df)
                logger.info(f"Загружен файл: {file.name} (строк: {len(df)})")

            except Exception as e:
                logger.error(f"Ошибка в файле {file.name}: {e}")

        self.df_all = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # -------------------------------------------------------------
    #   РАЗДЕЛЕНИЕ НА OK и BAD
    # -------------------------------------------------------------
    def _split_good_bad(self):
        if self.df_all.empty:
            self.ok_df = pd.DataFrame()
            self.bad_df = pd.DataFrame()
            return

        self.df_all["REFUSED"] = pd.to_numeric(
            self.df_all["REFUSED"], errors="coerce"
        ).fillna(0)

        has_refused = self.df_all.groupby("ORDER_ID")["REFUSED"].apply(
            lambda x: (x > 0).any()
        )

        bad_orders = has_refused[has_refused].index
        good_orders = has_refused[~has_refused].index

        self.bad_df = self.df_all[self.df_all["ORDER_ID"].isin(bad_orders)].copy()
        self.ok_df = self.df_all[self.df_all["ORDER_ID"].isin(good_orders)].copy()

    # -------------------------------------------------------------
    #   ПЕРЕМЕЩЕНИЕ ФАЙЛОВ
    # -------------------------------------------------------------
    def _move_processed_files(self):
        self.ok_folder.mkdir(parents=True, exist_ok=True)
        self.bad_folder.mkdir(parents=True, exist_ok=True)

        if self.df_all.empty:
            return

        for filename in self.df_all["__source_file__"].unique():
            order_id = self._extract_order_number_from_filename(filename)
            src = self.folder_path / filename

            if not src.exists():
                continue

            # bad или ok?
            if order_id in self.ok_df["ORDER_ID"].unique():
                dst = self.ok_folder / filename
            else:
                dst = self.bad_folder / filename

            try:
                #shutil.move(str(src), str(dst))
                logger.info(f"Файл {filename} перемещён в {dst}")
            except Exception as e:
                logger.error(f"Не удалось переместить {filename}: {e}")

    # -------------------------------------------------------------
    @staticmethod
    def _extract_order_number_from_filename(filename: str) -> str:
        return Path(filename).stem
