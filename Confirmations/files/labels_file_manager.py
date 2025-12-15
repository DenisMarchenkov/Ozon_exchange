import requests
from pathlib import Path
from datetime import datetime

from Common.logger import get_logger
from Confirmations.settings_app.settings_confirmations import ARCHIVE_DIR_LABELS

logger = get_logger("LabelsFileManager")


class LabelsFileManager:
    """
    Скачивание и сохранение PDF-файлов с наклейками Ozon.
    """

    def __init__(self):
        self.base_dir = self._get_labels_dir()

    # -------------------------------------------------

    @staticmethod
    def _get_labels_dir() -> Path:
        """
        Определяет и создаёт папку /Labels в корне проекта.
        """
        return ARCHIVE_DIR_LABELS

    # -------------------------------------------------

    def save(self, file_url: str) -> Path:
        """
        Скачивает PDF по URL и сохраняет в папку Labels.
        """
        filename = self._build_filename()
        file_path = self.base_dir / filename

        try:
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Файл наклеек сохранён: {file_path}")
            return file_path

        except requests.RequestException:
            logger.exception("Ошибка при скачивании PDF с наклейками")
            raise

    # -------------------------------------------------

    @staticmethod
    def _build_filename() -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"labels_{timestamp}.pdf"
