import json
import os
from pathlib import Path

import pandas as pd

from Common.base_reader_excel import BaseExcelReader
from Confirmations.settings_app.settings_confirmations import SETTINGS_APP_DIR


class ConfirmationsReader(BaseExcelReader):

    def __init__(self, folder_path: str, mapping_file: str = None):
        super().__init__(folder_path)

        if mapping_file is None:
            mapping_file = os.path.join(SETTINGS_APP_DIR, "column_map.json")

        with open(mapping_file, "r", encoding="utf-8") as f:
            self.column_map = json.load(f)

        self.required_columns = list(self.column_map.keys())

    def _read_file(self, file: Path) -> pd.DataFrame:
        df = pd.read_excel(file)
        return self._normalize_columns(df, file.name)

    def _normalize_columns(self, df: pd.DataFrame, filename: str) -> pd.DataFrame:
        new_names = {}

        for standard, aliases in self.column_map.items():
            for col in aliases:
                if col in df.columns:
                    new_names[col] = standard
                    break

        missing = [c for c in self.required_columns if c not in new_names.values()]
        if missing:
            raise ValueError(
                f"{filename}: отсутствуют обязательные колонки {missing}"
            )

        return df.rename(columns=new_names)
