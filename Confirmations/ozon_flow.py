from Common.logger import get_logger
from Confirmations.services.confirmations.confirmations_status_updater import ConfirmationsStatusUpdater
from Confirmations.services.dispatch.DispatchRetryService import DispatchRetryService
from Confirmations.services.dispatch.DispatchPrepareService import DispatchPrepareService
from Confirmations.services.dispatch.DispatchFilesService import DispatchFilesService
from Confirmations.services.labels.labels_generatior import LabelsGenerator
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder
from Confirmations.services.mailers.mailer_error import ErrorMailer

from Confirmations.utils.time import now_iso

logger = get_logger(__name__)


def run_ozon_flow(ozon_confirmations, confirmations_repo, dispatch_repo):
    """
    Запуск OZON-сценария.

    :param ozon_confirmations: список словарей с подтверждениями только для OZON
    :param confirmations_repo: репозиторий подтверждений
    :param dispatch_repo: репозиторий dispatch
    """
    if not ozon_confirmations:
        logger.info("Нет подтверждений для OZON")
        return

    # ============================================================
    # 1. ОБНОВЛЕНИЕ СТАТУСОВ OZON (ship)
    # ============================================================
    updater = ConfirmationsStatusUpdater()

    confirmed_orders = [c["posting_number"] for c in ozon_confirmations if c["status"] == "confirmed"]
    if confirmed_orders:
        logger.info(f"Переводим {len(confirmed_orders)} заказов со статусом confirmed")
        updater.process_deliveries(confirmed_orders)

    error_orders = [c["posting_number"] for c in ozon_confirmations if c["status"] == "error"]
    if error_orders:
        logger.info(f"Повторная попытка перевода {len(error_orders)} заказов со статусом error")
        updater.process_deliveries(error_orders)

    # ============================================================
    # 2. ПИСЬМО ОБ ОШИБКАХ
    # ============================================================
    remaining_errors = [c for c in ozon_confirmations if c["status"] == "error"]
    if remaining_errors:
        logger.warning("Остались неподтверждённые заказы после повторной попытки")
        mailer = ErrorMailer(error_rows=remaining_errors)
        mailer.send()
    else:
        logger.info("Нет данных для письма об ошибках")


    # ============================================================
    # 3. DISPATCH: RETRY → PREPARE
    # ============================================================
    labels_generator = LabelsGenerator()
    files_service = DispatchFilesService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        labels_generator=labels_generator,
        warehouse_builder_cls=lambda rows: WarehouseFileBuilder(rows, suffix="OZON"),
    )

    # --- retry ERROR dispatch ---
    retry_service = DispatchRetryService(
        dispatch_repo=dispatch_repo,
        files_service=files_service,
    )
    retry_service.retry_failed()

    # --- prepare новый dispatch с блокировкой только OZON-подтверждений ---
    dispatch_id = f"dispatch_{now_iso()}_OZON"
    prepare_service = DispatchPrepareService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service,
    )

    prepare_service.prepare(dispatch_id)

    logger.info(f"Dispatch {dispatch_id} завершён")