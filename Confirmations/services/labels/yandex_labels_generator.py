import time
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from Confirmations.api.yandex_labels_api import YandexLabelsAPI
from Common.time import now_iso
from Confirmations.services.labels.labels_file_manager import LabelsFileManager


@dataclass
class LabelDownloadResult:
    file_path: Optional[Path]
    failed: List[str]


class YandexLabelsGenerator:

    def __init__(
        self,
        confirmations_repo,
        logger,
        format_pdf: str = "A7",
        max_poll_attempts: int = 5,
        poll_delay: int = 5,
    ):
        self.api = YandexLabelsAPI(format_pdf=format_pdf)
        self.confirmations_repo = confirmations_repo
        self.logger = logger
        self.max_poll_attempts = max_poll_attempts
        self.poll_delay = poll_delay
        self.files = LabelsFileManager(prefix="yandex_labels__")

    # ============================================================
    # Метод, который вызывает DispatchFilesService
    # ============================================================
    def download(self, dispatch_id: str) -> LabelDownloadResult:

        items = self.confirmations_repo.get_items_by_dispatch(dispatch_id)
        if not items:
            return LabelDownloadResult(file_path=None, failed=[])

        order_ids = list({item["posting_number"] for item in items})
        
        self.confirmations_repo.update_stickers_status(order_ids, "creating", now_iso())

        report_id = self.api.create_report(order_ids)
        if not report_id:
            self.confirmations_repo.update_stickers_status(order_ids, "error", now_iso())
            return LabelDownloadResult(file_path=None, failed=order_ids)

        self.confirmations_repo.update_stickers_status(order_ids, "in_progress", now_iso())

        file_url = self._wait_until_ready(report_id)
        if not file_url:
            self.confirmations_repo.update_stickers_status(order_ids, "error", now_iso())
            return LabelDownloadResult(file_path=None, failed=order_ids)

        try:
            file_path = self.files.save_labels(file_url, custom_headers=self.api.headers)
            self.confirmations_repo.update_stickers_status(order_ids, "ready", now_iso())
            return LabelDownloadResult(file_path=file_path, failed=[])
        except Exception as e:
            self.logger.error(f"Ошибка сохранения ярлыков Yandex: {e}")
            self.confirmations_repo.update_stickers_status(order_ids, "error", now_iso())
            return LabelDownloadResult(file_path=None, failed=order_ids)

    # ============================================================
    # Ожидание готовности
    # ============================================================
    def _wait_until_ready(self, report_id: str) -> Optional[str]:

        for _ in range(self.max_poll_attempts):

            result = self.api.get_report_status(report_id=report_id)
            status = result.get("status")

            if status == "DONE":
                return result.get("file")

            if status in ["PROCESSING", "NEW", "PENDING"]:
                time.sleep(self.poll_delay)
                continue

            self.logger.error(f"Ошибка генерации ярлыков Yandex: статус={status}, ответ={result}")
            return None

        return None

