import os
import pandas as pd
from Common.logger import get_logger
from Common.settings import RECIPIENT_ADMIN
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.services.confirmations_recorder import ConfirmationsRecorder
from Confirmations.services.confirmations_status_updater import ConfirmationsStatusUpdater
from Confirmations.services.error_mailer import ErrorMailer
from Confirmations.settings_app.settings_confirmations import CONFIRMATIONS_DIR, SETTINGS_APP_DIR
from Confirmations.readers.excel_reader import ConfirmationsReader
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder
logger = get_logger("app_confirmations")


def main():
    logger.info("=== Запуск проверки подтверждений ===")

    # ============================================================
    # 1. ЧТЕНИЕ ПОДТВЕРЖДЕНИЙ И ФИКСАЦИЯ В БД
    # ============================================================
    reader = ConfirmationsReader(
        folder_path=CONFIRMATIONS_DIR,
        mapping_file=os.path.join(SETTINGS_APP_DIR, "column_map.json")
    )
    repo = ConfirmationsRepository()
    recorder = ConfirmationsRecorder(repo)
    recorder.record_from_dataframe(reader.df_all)


    # ============================================================
    # 2. ОБНОВЛЕНИЕ СТАТУСОВ НА OZON (ship)
    # ============================================================
    updater = ConfirmationsStatusUpdater()

    # 2.1 Переводим заказы со статусом "confirmed" → "awaiting_delivery"
    confirmed_orders = repo.get_list_postings_numbers_by_status("confirmed")
    if confirmed_orders:
        logger.info(f"Переводим {len(confirmed_orders)} заказов со статусом confirmed")
        updater.process_deliveries(confirmed_orders)

    # 2.2 Повторяем попытку для заказов со статусом "error" → "awaiting_delivery"
    error_orders = repo.get_list_postings_numbers_by_status("error")
    if error_orders:
        logger.info(f"Повторная попытка перевода {len(error_orders)} заказов со статусом error")
        updater.process_deliveries(error_orders)


    # ============================================================
    # 3. ЕСЛИ ОСТАЛИСЬ ПРОБЛЕМНЫЕ ПОДТВЕРЖДЕНИЯ — ГОТОВИМ УВЕДОМЛЕНИЕ (TODO)
    # ============================================================

    # remaining_errors = repo.get_by_status("error")
    # if remaining_errors:
    #     logger.warning("Остались неподтверждённые заказы после повторной попытки")
        # mailer = ErrorMailer(...)
        # mailer.send()


    # ============================================================
    # 4. ГЕНЕРАЦИЯ ФАЙЛА ДЛЯ СКЛАДА
    # ============================================================

    good_items = repo.get_items_for_warehouse("awaiting_delivery")

    if not good_items:
        logger.info("Нет данных для формирования файла склада")
    else:
        builder = WarehouseFileBuilder(
            rows=good_items,
            output_path=os.path.join(CONFIRMATIONS_DIR, "warehouse_file.xlsx")
        )
        builder.save()


    # ============================================================
    # 5. ГЕНЕРАЦИЯ НАКЛЕЕК (TODO)
    # ============================================================
    # labels = LabelsGenerator(...)
    # labels.create()

    # ============================================================
    # 6. ПИСЬМО СКЛАДУ (TODO)
    # ============================================================
    # mailer = WarehouseMailer(...)
    # mailer.send()

    logger.info("=== Проверка подтверждений завершена ===")

    row = repo.get_all()
    for r in row:
        print(r)
    print("--------------------------------------------")
    row = repo.get_all_items()
    for r in row:
        print(r)

if __name__ == "__main__":
    main()
