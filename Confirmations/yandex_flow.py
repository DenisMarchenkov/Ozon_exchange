from Common.logger import get_logger
from Common.time import now_iso
from Confirmations.services.dispatch.DispatchFilesService import DispatchFilesService
from Confirmations.services.dispatch.DispatchPrepareService import DispatchPrepareService
from Confirmations.services.dispatch.DispatchRetryService import DispatchRetryService
from Confirmations.services.labels.labels_file_manager import LabelsFileManager
from Confirmations.services.labels.yandex_labels_generator import YandexLabelsGenerator
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder

logger = get_logger(__name__)

def run_yandex_flow(yandex_confirmations, confirmations_repo, dispatch_repo,
                    business_id, headers):
    """
    Запуск YANDEX-сценария.
    """
    if not yandex_confirmations:
        logger.info("Нет подтверждений для Yandex")
        return

    posting_numbers = [c["posting_number"] for c in yandex_confirmations]

    # ============================================================
    # Инициализация генератора ярлыков
    # ============================================================
    labels_generator = YandexLabelsGenerator(
        business_id=business_id,
        headers=headers,
        file_manager=LabelsFileManager()
    )

    # ============================================================
    # Инициализация файлового сервиса Dispatch
    # ============================================================
    files_service = DispatchFilesService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        labels_generator=labels_generator,  # генератор встроен
        warehouse_builder_cls=lambda rows: WarehouseFileBuilder(rows, suffix="YANDEX"),
    )

    # ============================================================
    # Retry failed dispatch
    # ============================================================
    retry_service = DispatchRetryService(
        dispatch_repo=dispatch_repo,
        files_service=files_service,
    )
    retry_service.retry_failed()

    # ============================================================
    # Prepare новый dispatch
    # ============================================================
    dispatch_id = f"dispatch_{now_iso()}_YANDEX"
    prepare_service = DispatchPrepareService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service,
    )

    # Передаем только нужные подтверждения
    prepare_service.prepare(dispatch_id, postings_to_lock=posting_numbers)

    logger.info(f"Dispatch {dispatch_id} завершён")
    #return dispatch_id