import time
from pathlib import Path

from Common.logger import get_logger
from Common.settings import DEV_MODE
from Confirmations.api.ozon_labels_api import OzonLabelsAPI
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.files.labels_file_manager import LabelsFileManager

logger = get_logger("LabelsGenerator")


class LabelsGenerator:
    """
    Генерация и скачивание наклеек Ozon (FBS).
    """

    MAX_WAIT_TIME = 120          # сек
    CHECK_INTERVAL = 5           # сек

    def __init__(self):
        self.api = OzonLabelsAPI()
        self.repo = ConfirmationsRepository()
        self.files = LabelsFileManager()

    # -------------------------------------------------

    def generate(self):
        postings = []

        postings += self.repo.get_postings_by_status_and_stickers_status(
            "awaiting_delivery", "not_ready"
        )

        # добавляем заказы получение наклеек на которые ранее завершились ошибкой
        postings += self.repo.get_postings_by_status_and_stickers_status(
            "awaiting_delivery", "error"
        )

        postings = list(set(postings))

        if not postings:
            logger.info("Нет заказов для генерации наклеек")
            return

        logger.info(f"Запуск генерации наклеек для {len(postings)} заказов")

        # 1. отмечаем что начали
        self.repo.update_stickers_status(postings, "creating")

        # 2. создаём задачу
        task_id = self.api.create_task(postings)
        if not task_id:
            self.repo.update_stickers_status(
                postings,
                "error",
                "Не удалось создать задачу в Ozon"
            )
            return

        # 3. ждём выполнения
        self.repo.update_stickers_status(postings, "in_progress")
        result = self._wait_task(task_id)

        # 4. обработка результата
        if result["status"] == "completed" and result.get("file_url"):
            if DEV_MODE:
                logger.info(f"Наклейки сохранены")
            else:
                path = self.files.save(result["file_url"])
                logger.info(f"Наклейки сохранены: {path}")
            logger.info(f"Наклейки сохранены")
            self.repo.update_stickers_status(postings, "ready")
        else:
            error = result.get("error", "Ошибка генерации наклеек")
            self.repo.update_stickers_status(postings, "error", error)

    # -------------------------------------------------

    def _wait_task(self, task_id: str) -> dict:
        start = time.time()

        while time.time() - start < self.MAX_WAIT_TIME:
            info = self.api.get_task_status(task_id)
            status = info.get("status")

            if status == "completed":
                return info

            if status == "error":
                return {"status": "error", "error": "Ошибка на стороне Ozon"}

            logger.info(f"Задача наклеек в процессе ({status}), ожидание...")
            time.sleep(self.CHECK_INTERVAL)

        return {"status": "error", "error": "Таймаут ожидания наклеек"}
