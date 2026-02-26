import time
from pathlib import Path
from datetime import datetime

import requests

from Common.logger import get_logger
from Common.settings import DEV_MODE
from Confirmations.settings_app.settings_confirmations import ARCHIVE_DIR_LABELS

logger = get_logger(__name__)

class LabelsFileManager:
    """
    Скачивание и сохранение PDF-файлов с наклейками.
    """

    def __init__(self, prefix: str = "labels_file_"):
        self.base_dir = self._get_labels_dir()
        self.prefix = prefix

    # -------------------------------------------------

    @staticmethod
    def _get_labels_dir() -> Path:
        """
        Определяет и создаёт папку для хранения наклеек.
        """
        path = Path(ARCHIVE_DIR_LABELS)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # -------------------------------------------------

    def save_labels(self, file_url: str, custom_headers: dict = None) -> Path:
        file_path = self.base_dir / self._build_filename()

        if DEV_MODE:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists():
                file_path.write_bytes(b"%PDF-1.4 fake pdf content\n%%EOF")
            logger.info(f"[DEV MODE] Файл наклеек создан фиктивно: {file_path}")
            return file_path

        headers = {
            "User-Agent": "Mozilla/5.0",
        }
        if custom_headers:
            headers.update(custom_headers)

        for attempt in range(5):
            try:
                response = requests.get(
                    file_url,
                    headers=headers,
                    timeout=30,
                )

                if response.status_code == 200:
                    file_path.write_bytes(response.content)
                    logger.info(f"Файл наклеек сохранён: {file_path}")
                    return file_path

                logger.warning(
                    f"Попытка {attempt + 1}: "
                    f"статус {response.status_code}, ожидание..."
                )

            except requests.RequestException as e:
                logger.warning(f"Попытка {attempt + 1}: ошибка {e}")

            time.sleep(3)

        raise RuntimeError(f"Не удалось скачать PDF наклеек: {file_url}")

    def _build_filename(self) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"{self.prefix}{timestamp}.pdf"
