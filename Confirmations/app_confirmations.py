import os
from pprint import pprint

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

# def main():
#     loger.info("=== Запуск проверки подтверждений ===")
#
#
#     # 1. Читаем все подтверждения
#     reader = ConfirmationsReader(folder_path=CONFIRMATIONS_DIR,
#                                  mapping_file=os.path.join(SETTINGS_APP_DIR, "column_map.json")
#                                  )
#
#     # 1.1 Пишем в бд
#     service = ConfirmationsRecorder()
#     service.process_confirmations(
#         ok_df=reader.ok_df,
#         refused_df=reader.bad_df,
#     )
#
#
#     # 2. Если есть дефектура → письмо
#     # if not reader.bad_df.empty:
#     #     mailer = DefecturaMailer(
#     #         df=reader.bad_df,
#     #         to=RECIPIENT_ADMIN,
#     #         smtp_user=MAILER_LOGIN,
#     #         smtp_password=MAILER_PASSWORD,
#     #     )
#     #     mailer.send()
#
#
#     # 3. Переводим все confirmed заказы в awaiting_delivery
#     repo = ConfirmationsRepository()
#     confirmed_confirmations = repo.get_list_postings_numbers_by_status("confirmed")
#     ConfirmationsStatusUpdater().process_deliveries(confirmed_confirmations)
#
#     # 3.1 Если были ошибки отправляем письмо
#     bad_confirmations = repo.get_by_status("awaiting_confirmation")
#     if bad_confirmations:
#         loger.info(f"Отправляем письмо об ошибках")
#         # mailer = ErrorMailer(
#         #     bad_confirmations=bad_confirmations,
#         #     to=RECIPIENT_ADMIN,
#         #     smtp_user="MAILER_LOGIN",
#         #     smtp_password="MAILER_PASSWORD",
#         # )
#         # mailer.send()
#
#
#     # 4. Формируем файл для склада
#     builder =  WarehouseFileBuilder(df=reader.ok_df,
#                                     output_path=os.path.join(CONFIRMATIONS_DIR, 'warehouse_file.xlsx')
#                                     )
#     builder.save()
#
#     # 5. Получаем наклейки
#
#     # 6. Письмо складу (наклейки, файл подбора товаров)
#     loger.info("=== Проверка подтверждений закончена ===")


def main():
    logger.info("=== Запуск проверки подтверждений ===")

    # ============================================================
    # 1. ЧТЕНИЕ ПОДТВЕРЖДЕНИЙ И ФИКСАЦИЯ В БД
    # ============================================================
    reader = ConfirmationsReader(
        folder_path=CONFIRMATIONS_DIR,
        mapping_file=os.path.join(SETTINGS_APP_DIR, "column_map.json")
    )

    recorder = ConfirmationsRecorder()
    recorder.process_confirmations(
        ok_df=reader.ok_df,
        refused_df=reader.bad_df,
    )
    print(reader.df_all.columns.tolist())

    repo = ConfirmationsRepository()
    row = repo.get_all_items()
    for r in row:
        print(r)

    row = repo.get_all()
    for r in row:
        print(r)

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
    # 3. ЕСЛИ ОСТАЛИСЬ ПРОБЛЕМНЫЕ ПОДТВЕРЖДЕНИЯ — ГОТОВИМ УВЕДОМЛЕНИЕ
    # ============================================================

    remaining_errors = repo.get_by_status("error")
    if remaining_errors:
        logger.warning("Остались неподтверждённые заказы после повторной попытки")
        # mailer = ErrorMailer(...)
        # mailer.send()

    # ============================================================
    # 4. ГЕНЕРАЦИЯ ФАЙЛА ДЛЯ СКЛАДА
    # ============================================================

    builder = WarehouseFileBuilder(
        df=reader.ok_df,
        output_path=os.path.join(CONFIRMATIONS_DIR, 'warehouse_file.xlsx')
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


if __name__ == "__main__":
    main()

