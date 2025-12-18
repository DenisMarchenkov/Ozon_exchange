import time
from pathlib import Path
from Common.logger import get_logger
from Confirmations.api.ozon_labels_api import OzonLabelsAPI
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.files.labels_file_manager import LabelsFileManager

logger = get_logger(__name__)

class LabelsGenerator:
    MAX_WAIT_TIME = 120
    CHECK_INTERVAL = 5

    def __init__(self):
        self.api = OzonLabelsAPI()
        self.repo = ConfirmationsRepository()
        self.files = LabelsFileManager()

    def download(self, dispatch_id) -> Path | None:
        #postings = self.repo.get_postings_by_status_and_stickers_status("awaiting_delivery", "not_ready")
        #postings += self.repo.get_postings_by_status_and_stickers_status("awaiting_delivery", "error")

        postings = self.repo.get_postings_by_dispatch(dispatch_id)

        postings = list(set(postings))

        if not postings:
            logger.info("Нет заказов для генерации наклеек")
            return None

        logger.info(f"Генерация наклеек для {len(postings)} заказов")
        self.repo.update_stickers_status(postings, "creating")

        task_id = self.api.create_task(postings)
        if not task_id:
            self.repo.update_stickers_status(postings, "error", "Не удалось создать задачу")
            return None

        self.repo.update_stickers_status(postings, "in_progress")
        result = self._wait_task(task_id)

        if result.get("status") == "completed" and result.get("file_url"):
            path = self.files.save(result["file_url"])
            self.repo.update_stickers_status(postings, "ready")
            logger.info(f"Наклейки сохранены: {path}")
            return path
        else:
            self.repo.update_stickers_status(postings, "error", result.get("error", "Ошибка генерации"))
            return None

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
