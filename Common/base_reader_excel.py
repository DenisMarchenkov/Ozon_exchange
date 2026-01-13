from pathlib import Path
import pandas as pd

from Common.file_policy import FilePolicy
from Common.logger import get_logger

logger = get_logger(__name__)


class BaseExcelReader:
    file_pattern = "*.xls"

    def __init__(self, folder_path: str, file_policy: FilePolicy | None = None):
        self.folder_path = Path(folder_path)
        self.file_policy = file_policy

    def filter_files(self, files: list[Path]) -> list[Path]:
        if self.file_policy:
            return self.file_policy.filter(files)
        return files

    def read(self) -> pd.DataFrame:
        files = list(self.folder_path.glob(self.file_pattern))
        files = self.filter_files(files)

        if not files:
            logger.warning("Нет подходящих файлов для обработки")
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
        """
        Базовая реализация.
        Можно (и нужно) переопределять в наследниках.
        """
        return pd.read_excel(file)
