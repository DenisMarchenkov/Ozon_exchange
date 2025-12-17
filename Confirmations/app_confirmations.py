import os

from Common.logger import get_logger
from Common.settings import DB_PATH
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.db_confirmations.dispatch_repository import DispatchRepository
from Confirmations.services.confirmations_recorder import ConfirmationsRecorder
from Confirmations.services.confirmations_status_updater import ConfirmationsStatusUpdater
from Confirmations.services.confirmations_reader import ConfirmationsReader
from Confirmations.services.dispatch_prepare import DispatchPrepareService
from Confirmations.services.labels_generatior import LabelsGenerator
from Confirmations.services.mailer_error import ErrorMailer
from Confirmations.services.mailer_shortage import ShortageMailer
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder
from Confirmations.services.file_manager import ArchiveFileManager
from Confirmations.settings_app.settings_confirmations import (CONFIRMATIONS_DIR,
                                                               SETTINGS_APP_DIR,
                                                               ARCHIVE_DIR_CONFIRMATIONS)
from Confirmations.utils.time import now_iso

logger = get_logger("app_confirmations")


def main():
    logger.info("=== Запуск проверки подтверждений ===")

    # ============================================================
    # 1. ЧТЕНИЕ ПОДТВЕРЖДЕНИЙ
    # ============================================================
    reader = ConfirmationsReader(
        folder_path=CONFIRMATIONS_DIR,
        mapping_file=os.path.join(SETTINGS_APP_DIR, "column_map.json")
    )
    df = reader.read()


    # ============================================================
    # 2. ЗАПИСЬ ДАННЫХ В БД
    # ============================================================
    repo = ConfirmationsRepository()
    recorder = ConfirmationsRecorder(repo)
    recorder.record_from_dataframe(df)


    # ============================================================
    # 3. АРХИВАЦИЯ ОБРАБОТАННЫХ ФАЙЛОВ
    # ============================================================
    file_manager = ArchiveFileManager(inbox_dir=CONFIRMATIONS_DIR,
                                      archive_dir=ARCHIVE_DIR_CONFIRMATIONS,
                                      dry_run=True)
    file_manager.archive_all()


    # ============================================================
    # 4. ОБНОВЛЕНИЕ СТАТУСОВ НА OZON (ship)
    # ============================================================
    updater = ConfirmationsStatusUpdater()

    # 4.1 Переводим заказы со статусом "confirmed" → "awaiting_delivery"
    confirmed_orders = repo.get_list_postings_numbers_by_status("confirmed")
    if confirmed_orders:
        logger.info(f"Переводим {len(confirmed_orders)} заказов со статусом confirmed")
        updater.process_deliveries(confirmed_orders)

    # 4.2 Повторяем попытку для заказов со статусом "error" → "awaiting_delivery"
    error_orders = repo.get_list_postings_numbers_by_status("error")
    if error_orders:
        logger.info(f"Повторная попытка перевода {len(error_orders)} заказов со статусом error")
        updater.process_deliveries(error_orders)


    # ============================================================
    # 5. ЕСЛИ ОСТАЛИСЬ ПРОБЛЕМНЫЕ ПОДТВЕРЖДЕНИЯ — ГОТОВИМ УВЕДОМЛЕНИЕ
    # ============================================================
    remaining_errors = repo.get_items_for_error_mailer("error")

    if not remaining_errors:
        logger.info("Нет данных для создания письма об ошибках после повторной попытки")
    else:
        logger.warning("Остались неподтверждённые заказы после повторной попытки")
        mailer = ErrorMailer(error_rows=remaining_errors)
        # mailer.send()


    # ============================================================
    # 6. ЕСЛИ ВЫЯВЛЕНЫ ОТКАЗАННЫЕ ПОЗИЦИИ - ГОТОВИМ УВЕДОМЛЕНИЕ
    # ============================================================
    refused_items = repo.get_items_by_statuses_conf_and_item("awaiting_confirmation", "REFUSED")
    if not refused_items:
        logger.info("Нет данных для для создания письма о нехватке товара")
    else:
        logger.warning("Есть отказанные позиции")
        mailer = ShortageMailer(shortage_rows=refused_items)
        # mailer.send()


    # ============================================================
    # 7. ГЕНЕРАЦИЯ ФАЙЛОВ НА ОТПРАВКУ
    # ============================================================
    dispatch_id = f"dispatch_{now_iso()}"
    dispatch_repo = DispatchRepository(DB_PATH)
    confirmations_repo = ConfirmationsRepository(DB_PATH)
    labels_generator = LabelsGenerator()
    prepare_service = DispatchPrepareService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        labels_generator=labels_generator,
        warehouse_builder_cls=WarehouseFileBuilder
    )

    # ЯВНО выбираем postings
    posting_numbers = confirmations_repo.get_postings_by_status_and_stickers_status(
        status="awaiting_delivery",
        stickers_status="not_ready",
    )


    if not posting_numbers:
        logger.info("Нет postings для формирования dispatch")
        return

    logger.info(f"Найдено postings: {len(posting_numbers)}")

    # Подготовка dispatch
    prepare_service.prepare(
        dispatch_id=dispatch_id,
        posting_numbers=posting_numbers,
    )

    logger.info(f"Dispatch {dispatch_id} подготовлен")



    # ============================================================
    # TODO 8. ОТПРАВКА ПИСЬМА НА СКЛАД
    # ============================================================


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

