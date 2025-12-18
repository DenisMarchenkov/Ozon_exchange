# from pathlib import Path
# from Confirmations.db_confirmations.dispatchs_repository import DispatchRepository
# from Common.logger import get_logger
# from Confirmations.utils.time import now_iso
#
# logger = get_logger(__name__)
#
# class DispatchPrepareService:
#     def __init__(self, dispatch_repo: DispatchRepository, confirmations_repo, labels_generator, warehouse_builder_cls):
#         self.dispatch_repo = dispatch_repo
#         self.confirmations_repo = confirmations_repo
#         self.labels_generator = labels_generator
#         self.warehouse_builder_cls = warehouse_builder_cls
#
#     def prepare(self, dispatch_id: str):
#         logger.info(f"Подготовка dispatch {dispatch_id}")
#         if not self.dispatch_repo.exists(dispatch_id):
#             self.dispatch_repo.create_dispatch(dispatch_id, now_iso())
#
#         try:
#             label_path: Path = self.labels_generator.download()
#             if label_path and label_path.exists():
#                 self.dispatch_repo.add_file(dispatch_id, "LABEL", label_path)
#
#             postings = self.confirmations_repo.get_postings_by_status_and_stickers_status("awaiting_delivery", "ready")
#             self.dispatch_repo.add_postings(dispatch_id, postings)
#
#             good_items = self.confirmations_repo.get_items_for_warehouse("awaiting_delivery", "ready")
#             if good_items:
#                 builder = self.warehouse_builder_cls(rows=good_items)
#                 warehouse_path = builder.build()
#                 if warehouse_path.exists():
#                     self.dispatch_repo.add_file(dispatch_id, "WAREHOUSE", warehouse_path)
#
#             self.dispatch_repo.update_status(dispatch_id, "PREPARED")
#         except Exception:
#             logger.exception(f"Ошибка при подготовке dispatch {dispatch_id}")
#             self.dispatch_repo.update_status(dispatch_id, "ERROR")
#             raise
from pathlib import Path
from Common.logger import get_logger
from Confirmations.utils.time import now_iso

logger = get_logger(__name__)


class DispatchPrepareService:
    def __init__(
        self,
        dispatch_repo,
        confirmations_repo,
        labels_generator,
        warehouse_builder_cls,
    ):
        self.dispatch_repo = dispatch_repo
        self.confirmations_repo = confirmations_repo
        self.labels_generator = labels_generator
        self.warehouse_builder_cls = warehouse_builder_cls

    def prepare(self, dispatch_id: str, posting_numbers: list[str]):
        logger.info(f"Подготовка dispatch {dispatch_id}")

        if not posting_numbers:
            raise ValueError("Нельзя подготовить dispatch без postings")

        REQUIRED_FILE_TYPES = {"LABEL", "WAREHOUSE"}

        # 1. Создаём dispatch (если нет)
        if not self.dispatch_repo.exists(dispatch_id):
            self.dispatch_repo.create_dispatch(dispatch_id, now_iso())

        try:
            # 2. Привязываем postings (строго те, что передали)
            self.confirmations_repo.lock_postings_for_dispatch(dispatch_id)

            # 3. Скачиваем labels
            label_path: Path | None = self.labels_generator.download(dispatch_id)
            if label_path and label_path.exists():
                self.dispatch_repo.add_file(dispatch_id, "LABEL", label_path)

            # 4. Берём items ТОЛЬКО по этим postings
            items = self.confirmations_repo.get_items_by_dispatch(dispatch_id)

            if items:
                builder = self.warehouse_builder_cls(rows=items)
                warehouse_path = builder.build()

                if warehouse_path and warehouse_path.exists():
                    self.dispatch_repo.add_file(
                        dispatch_id,
                        "WAREHOUSE",
                        warehouse_path,
                    )

            # 5. Финальный статус
            file_types = set(
                self.dispatch_repo.get_file_types(dispatch_id)
            )

            missing = REQUIRED_FILE_TYPES - file_types
            if missing:
                logger.error(f"Dispatch {dispatch_id} не готов. Отсутствуют файлы: {', '.join(missing)}")
                raise RuntimeError(
                    f"Dispatch {dispatch_id} не готов. "
                    f"Отсутствуют файлы: {', '.join(missing)}"
                )

            self.dispatch_repo.update_status(dispatch_id, "PREPARED")

        except Exception:
            logger.exception(f"Ошибка при подготовке dispatch {dispatch_id}")
            self.dispatch_repo.update_status(dispatch_id, "ERROR")
            raise
