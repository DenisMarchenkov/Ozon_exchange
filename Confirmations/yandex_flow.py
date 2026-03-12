from Common.logger import get_logger
from Common.time import now_iso
from Confirmations.services.dispatch.DispatchFilesService import DispatchFilesService
from Confirmations.services.dispatch.DispatchPrepareService import DispatchPrepareService
from Confirmations.services.dispatch.DispatchRetryService import DispatchRetryService
from Confirmations.services.labels.yandex_labels_generator import YandexLabelsGenerator
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder

logger = get_logger(__name__)


def run_yandex_flow(
    yandex_confirmations,
    confirmations_repo,
    dispatch_repo,
):
    if yandex_confirmations:
        from Confirmations.api.yandex_confirmations_api import YandexConfirmationsAPI
        yandex_api = YandexConfirmationsAPI()

        # ============================================================
        # 0. Перевод подтвержденных заказов в "ожидает отгрузки"
        # ============================================================
        orders_to_update = []
        for confirmation in yandex_confirmations:
            if confirmation.get("status") == "confirmed":
                orders_to_update.append(confirmation.get("posting_number"))

        if orders_to_update:
            logger.info(f"Обнаружено {len(orders_to_update)} заказов Yandex для перевода в READY_TO_SHIP.")
            success = yandex_api.update_order_statuses(orders_to_update, "PROCESSING", "READY_TO_SHIP")
            if success:
                for posting_number in orders_to_update:
                    logger.info(f"Yandex Одобрено для ship: {posting_number}")
                    confirmations_repo.update_status(posting_number, "awaiting_delivery")
            else:
                logger.error("Не удалось обновить статусы заказов в Yandex API. Локальные статусы не изменены.")
    else:
        logger.info("Нет НОВЫХ подтверждений для Yandex (пропуск обновления статусов)")

    # ============================================================
    # 1. Формируем dispatch_id
    # ============================================================
    dispatch_id = f"dispatch_{now_iso()}_YANDEX"

    # ============================================================
    # 2. Инициализация генератора ярлыков
    # ============================================================
    labels_generator = YandexLabelsGenerator(
        confirmations_repo=confirmations_repo,
        logger=logger,
    )

    # ============================================================
    # 3. Инициализация файлового сервиса
    # ============================================================
    files_service = DispatchFilesService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        labels_generator=labels_generator,
        warehouse_builder_cls=lambda rows: WarehouseFileBuilder(rows, suffix="YANDEX"),
    )

    # ============================================================
    # 4. Retry failed dispatch
    # ============================================================
    retry_service = DispatchRetryService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service,
    )
    retry_service.retry_failed()

    # ============================================================
    # 5. Подготовка dispatch через общий сервис
    # ============================================================
    prepare_service = DispatchPrepareService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service,
    )

    from Confirmations.settings_app.settings_confirmations import YANDEX_DIVISION
    prepare_service.prepare(dispatch_id, divisions=tuple(YANDEX_DIVISION))

    logger.info(f"Dispatch {dispatch_id} завершён")