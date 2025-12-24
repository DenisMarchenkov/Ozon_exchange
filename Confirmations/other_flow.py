from Common.logger import get_logger
from Confirmations.services.dispatch.DispatchFilesService import DispatchFilesService
from Confirmations.services.dispatch.DispatchPrepareService import DispatchPrepareService
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder
from Common.time import now_iso

logger = get_logger(__name__)


def run_other_flow(other_confirmations, confirmations_repo, dispatch_repo):
    if not other_confirmations:
        logger.info("Нет подтверждений для OTHERS")
        return

    posting_numbers = [c["posting_number"] for c in other_confirmations]

    files_service = DispatchFilesService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        labels_generator=None,                      # без наклеек
        warehouse_builder_cls=lambda rows: WarehouseFileBuilder(rows, suffix="OTHERS"),
    )

    # --- prepare новый dispatch с блокировкой только подтверждений ---
    dispatch_id = f"dispatch_{now_iso()}_OTHERS"

    prepare_service = DispatchPrepareService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service,
    )

    # ВАЖНО: передаём postings явно
    prepare_service.prepare(
        dispatch_id,
        postings_to_lock=posting_numbers,
    )

    logger.info(f"Dispatch {dispatch_id} завершён")

