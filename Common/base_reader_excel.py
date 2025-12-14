from pathlib import Path
import pandas as pd
from Common.logger import get_logger

logger = get_logger("ExcelReader")


class BaseExcelReader:
    file_pattern = "*.xls"

    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)

    def read(self) -> pd.DataFrame:
        files = list(self.folder_path.glob(self.file_pattern))

        if not files:
            logger.warning(f"Нет файлов {self.file_pattern} в {self.folder_path}")
            return pd.DataFrame()

        frames = []

        for file in files:
            try:
                df = self._read_file(file)
                df["__source_file__"] = file.name
                frames.append(df)

                logger.info(f"Загружен файл {file.name} ({len(df)} строк)")
            except Exception as e:
                logger.error(f"Ошибка чтения {file.name}: {e}")

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def _read_file(self, file: Path) -> pd.DataFrame:
        """Можно переопределять"""
        return pd.read_excel(file)
