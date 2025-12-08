import os
from pprint import pprint

from Common.logger import get_logger
from Common.settings import CONFIRMATIONS_DIR
from Confirmations.readers.excel_reader import ConfirmationsReader
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder
loger = get_logger("app_confirmations")

def main():
    loger.info("=== Запуск проверки подтверждений ===")
    reader = ConfirmationsReader(CONFIRMATIONS_DIR)
    df_all = reader.df_all
    df_ok = reader.ok_df
    df_bad = reader.bad_df

    pprint(df_ok)
    pprint(df_bad)

    builder =  WarehouseFileBuilder(df=df_ok, output_path=os.path.join(CONFIRMATIONS_DIR, 'warehouse_file.xlsx'))
    builder.save()

    loger.info("=== Проверка подтверждений закончена ===")


if __name__ == "__main__":
    main()
