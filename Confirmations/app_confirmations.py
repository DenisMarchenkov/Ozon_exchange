import os
from pprint import pprint

from Common.logger import get_logger
from Confirmations.db_confirmations.confirmation_repository import ConfirmationsRepository
from Confirmations.services.confirmations_recorder import ConfirmationsRecorder
from Confirmations.services.confirmations_status_updater import ConfirmationsStatusUpdater
from Confirmations.settings_app.settings_confirmations import CONFIRMATIONS_DIR, SETTINGS_APP_DIR
from Confirmations.readers.excel_reader import ConfirmationsReader
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder
loger = get_logger("app_confirmations")

def main():
    loger.info("=== Запуск проверки подтверждений ===")


    # 1. Читаем все подтверждения
    reader = ConfirmationsReader(folder_path=CONFIRMATIONS_DIR,
                                 mapping_file=os.path.join(SETTINGS_APP_DIR, "column_map.json")
                                 )

    # 1.1 Пишем в бд
    service = ConfirmationsRecorder()
    service.process_confirmations(
        ok_df=reader.ok_df,
        refused_df=reader.bad_df,
    )


    # 2. Если есть дефектура → письмо
    # if not reader.bad_df.empty:
    #     mailer = DefecturaMailer(
    #         df=reader.bad_df,
    #         to=RECIPIENT_ADMIN,
    #         smtp_user=MAILER_LOGIN,
    #         smtp_password=MAILER_PASSWORD,
    #     )
    #     mailer.send()


    # 3. Переводим все ОК заказы в awaiting_delivery
    packages = reader.ok_df["ORDER_ID"].unique().tolist()
    updater = ConfirmationsStatusUpdater()
    updater.process_deliveries(packages)

    # 4. Формируем файл для склада
    builder =  WarehouseFileBuilder(df=reader.ok_df,
                                    output_path=os.path.join(CONFIRMATIONS_DIR, 'warehouse_file.xlsx')
                                    )
    builder.save()

    # 5. Получаем наклейки

    # 6. Письмо складу (наклейки, файл подбора товаров)
    loger.info("=== Проверка подтверждений закончена ===")


if __name__ == "__main__":
    main()
