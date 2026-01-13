from pathlib import Path

from Common.time import now_iso
from Common.logger import get_logger
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.services.labels.labels_file_manager import LabelsFileManager


logger = get_logger(__name__)

class YandexLabelsGenerator:
    """
    Класс генерации ярлыков для Yandex
    """
    MAX_WAIT_TIME = 120
    CHECK_INTERVAL = 5

    def __init__(self, business_id: int, headers: dict, file_manager=None):
        #todo YandexLabelsAPI
        self.api = YandexLabelGenerator(business_id=business_id, headers=headers)
        self.repo = ConfirmationsRepository()
        self.files = file_manager or LabelsFileManager()

    def generate_for_dispatch(self, dispatch_id) -> Path | None:
        """
        Генерация ярлыков для dispatch с использованием LabelsFileManager.
        """
        postings = self.repo.get_postings_by_dispatch(dispatch_id)
        postings = list(set(postings))

        if not postings:
            logger.info("Нет заказов для генерации ярлыков Yandex")
            return None

        logger.info(f"Генерация ярлыков для {len(postings)} заказов")
        self.repo.update_stickers_status(postings, "creating", now_iso())

        order_ids = [p["order_id"] for p in postings]
        try:
            result_file_url = self.api.generate_labels_for_orders(order_ids)
        except Exception as e:
            logger.error(f"Ошибка генерации ярлыков: {e}")
            self.repo.update_stickers_status(postings, "error", now_iso())
            return None

        if result_file_url:
            path = self.files.save_labels(result_file_url)
            self.repo.update_stickers_status(postings, "ready", now_iso())
            logger.info(f"Ярлыки Yandex сохранены: {path}")
            return path
        else:
            self.repo.update_stickers_status(postings, "error", now_iso())
            logger.error("Не удалось получить ярлыки Yandex")
            return None