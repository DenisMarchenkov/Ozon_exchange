import os

from Common.logger import get_logger
from Common.settings import DB_PATH

from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.db_confirmations.dispatch_repository import DispatchRepository

from Confirmations.services.confirmations.confirmations_reader import ConfirmationsReader
from Confirmations.services.confirmations.confirmations_recorder import ConfirmationsRecorder
from Confirmations.services.confirmations.confirmations_status_updater import ConfirmationsStatusUpdater

from Confirmations.services.dispatch.DispatchRetryService import DispatchRetryService
from Confirmations.services.dispatch.DispatchPrepareService import DispatchPrepareService
from Confirmations.services.dispatch.DispatchFilesService import DispatchFilesService

from Confirmations.services.labels.labels_generatior import LabelsGenerator
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder

from Confirmations.services.mailers.mailer_dispatch import DispatchMailer
from Confirmations.services.mailers.mailer_error import ErrorMailer
from Confirmations.services.mailers.mailer_shortage import ShortageMailer

from Confirmations.services.archive_file_manager import ArchiveFileManager

from Confirmations.settings_app.settings_confirmations import (
    CONFIRMATIONS_DIR,
    SETTINGS_APP_DIR,
    ARCHIVE_DIR_CONFIRMATIONS,
)

from Confirmations.utils.time import now_iso


logger = get_logger(__name__)


def main():
    logger.info("=== Запуск проверки подтверждений ===")

    # ============================================================
    # 1. ЧТЕНИЕ ПОДТВЕРЖДЕНИЙ
    # ============================================================
    reader = ConfirmationsReader(
        folder_path=CONFIRMATIONS_DIR,
        mapping_file=os.path.join(SETTINGS_APP_DIR, "column_map.json"),
    )
    df = reader.read()

    # ============================================================
    # 2. ЗАПИСЬ В БД
    # ============================================================
    confirmations_repo = ConfirmationsRepository(DB_PATH)
    recorder = ConfirmationsRecorder(confirmations_repo)
    recorder.record_from_dataframe(df)

    # ============================================================
    # 3. АРХИВАЦИЯ ФАЙЛОВ
    # ============================================================
    file_manager = ArchiveFileManager(
        inbox_dir=CONFIRMATIONS_DIR,
        archive_dir=ARCHIVE_DIR_CONFIRMATIONS,
        dry_run=True,
    )
    file_manager.archive_all()

    # ============================================================
    # 4. ОБНОВЛЕНИЕ СТАТУСОВ OZON (ship)
    # ============================================================
    updater = ConfirmationsStatusUpdater()

    confirmed_orders = confirmations_repo.get_list_postings_numbers_by_status("confirmed")
    if confirmed_orders:
        logger.info(f"Переводим {len(confirmed_orders)} заказов со статусом confirmed")
        updater.process_deliveries(confirmed_orders)

    error_orders = confirmations_repo.get_list_postings_numbers_by_status("error")
    if error_orders:
        logger.info(f"Повторная попытка перевода {len(error_orders)} заказов со статусом error")
        updater.process_deliveries(error_orders)

    # ============================================================
    # 5. ПИСЬМО ОБ ОШИБКАХ
    # ============================================================
    remaining_errors = confirmations_repo.get_items_for_error_mailer("error")
    if remaining_errors:
        logger.warning("Остались неподтверждённые заказы после повторной попытки")
        mailer = ErrorMailer(error_rows=remaining_errors)
        # mailer.send()
    else:
        logger.info("Нет данных для письма об ошибках")

    # ============================================================
    # 6. ПИСЬМО О НЕХВАТКЕ
    # ============================================================
    refused_items = confirmations_repo.get_items_by_statuses_conf_and_item(
        "awaiting_confirmation", "REFUSED"
    )
    if refused_items:
        logger.warning("Есть отказанные позиции")
        mailer = ShortageMailer(shortage_rows=refused_items)
        # mailer.send()
    else:
        logger.info("Нет данных для письма о нехватке товара")

    # ============================================================
    # 7. DISPATCH: RETRY → PREPARE
    # ============================================================
    dispatch_repo = DispatchRepository(DB_PATH)

    labels_generator = LabelsGenerator()
    files_service = DispatchFilesService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        labels_generator=labels_generator,
        warehouse_builder_cls=WarehouseFileBuilder,
    )

    # --- retry ERROR dispatch ---
    retry_service = DispatchRetryService(
        dispatch_repo=dispatch_repo,
        files_service=files_service,
    )
    retry_service.retry_failed()

    # --- prepare новый dispatch ---
    dispatch_id = f"dispatch_{now_iso()}"
    prepare_service = DispatchPrepareService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service,
    )
    prepare_service.prepare(dispatch_id)

    logger.info(f"Dispatch {dispatch_id} завершён")

    # ============================================================
    # 8. ОТПРАВКА НА СКЛАД
    # ============================================================
    departures_for_send = dispatch_repo.get_dispatch_id_by_status("PREPARED")

    for dispatch in departures_for_send:
        d_id = dispatch.get("id")

        try:
            dispatch_files = dispatch_repo.get_files(d_id)
            if not dispatch_files:
                raise RuntimeError("Нет файлов для отправки")

            mailer = DispatchMailer(dispatch_files)
            mailer.send()

            dispatch_repo.update_status(d_id, "SHIPPED_TO_STOCK")

        except Exception:
            logger.exception(f"Ошибка отправки dispatch {d_id}")
            dispatch_repo.update_status(d_id, "ERROR")

    logger.info("=== Проверка подтверждений завершена ===")


if __name__ == "__main__":
    main()
    repo_conf = ConfirmationsRepository(DB_PATH)
    repo_disp = DispatchRepository(DB_PATH)
    row = repo_conf.get_all()

    for r in row:
        print(r)
    print("--------------------------------------------")

    row = repo_conf.get_all_items()
    for r in row:
        print(r)
    print("--------------------------------------------")

    row = repo_disp.get_all_dispatch()
    for r in row:
        print(r)
    print("--------------------------------------------")

    row = repo_disp.get_all_files()
    for r in row:
        print(r)
    print("--------------------------------------------")