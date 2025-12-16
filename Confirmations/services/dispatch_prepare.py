from pathlib import Path
from Confirmations.db_confirmations.dispatchs_repository import DispatchRepository
from Common.logger import get_logger
from Confirmations.utils.time import now_iso

logger = get_logger("DispatchPrepareService")


class DispatchPrepareService:
    """
    Сервис подготовки dispatch:
    - генерирует файлы для склада и наклейки
    - сохраняет их в БД через DispatchRepository
    """

    def __init__(
        self,
        dispatch_repo: DispatchRepository,
        confirmations_repo,
        labels_generator,
        warehouse_builder_cls,
    ):
        self.dispatch_repo = dispatch_repo
        self.confirmations_repo = confirmations_repo
        self.labels_generator = labels_generator
        self.warehouse_builder_cls = warehouse_builder_cls
        self.logger = logger

    def prepare(self, dispatch_id: str):
        self.logger.info(f"Подготовка dispatch {dispatch_id}")

        # Если dispatch еще не существует — создаем
        if not self.dispatch_repo.exists(dispatch_id):
            self.dispatch_repo.create_dispatch(dispatch_id, now_iso())

        try:
            # -------------------------------
            # Генерация наклеек
            # -------------------------------
            label_path: Path = self.labels_generator.download()
            if label_path and label_path.exists():
                self.dispatch_repo.add_file(
                    dispatch_id=dispatch_id,
                    file_type="LABEL",
                    file_path=label_path
                )
                self.logger.info(f"Наклейки сохранены: {label_path}")

            # -------------------------------
            # Генерация файла для склада
            # -------------------------------
            good_items = self.confirmations_repo.get_items_for_warehouse(
                "awaiting_delivery", "ready"
            )

            if not good_items:
                self.logger.info("Нет данных для формирования файла склада")
            else:
                builder = self.warehouse_builder_cls(rows=good_items)
                warehouse_path = builder.build()

                if warehouse_path.exists():
                    self.dispatch_repo.add_file(
                        dispatch_id=dispatch_id,
                        file_type="WAREHOUSE",
                        file_path=warehouse_path
                    )
                    self.logger.info(f"Файл склада сохранён: {warehouse_path}")

            # -------------------------------
            # Обновляем статус dispatch
            # -------------------------------
            self.dispatch_repo.update_status_dispatch(dispatch_id, "PREPARED")

        except Exception:
            self.logger.exception(f"Ошибка при подготовке dispatch {dispatch_id}")
            self.dispatch_repo.update_status_dispatch(dispatch_id, "ERROR")
            raise
