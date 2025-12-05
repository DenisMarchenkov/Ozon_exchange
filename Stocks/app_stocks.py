from Stocks.readers.excel_reader import prepare_offers_data
from Stocks.api.ozon_api import update_stocks
from Common.file_utils import copy_file_with_timestamp
from Common.settings import API_TOKEN, SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER
from Common.logger import get_logger
logger = get_logger("Stocks")

def start_exchange_stock(file):
    """
    Основная функция запуска обмена товарными остатками.
    """
    logger.info("=== Запуск обмена товарными остатками ===")
    offers = prepare_offers_data(file)
    update_stocks(API_TOKEN, offers)
    logger.info("=== Обмен товарными остатками завершен ===")

def main():
    file_supplier = copy_file_with_timestamp(SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER)
    start_exchange_stock(file_supplier)

if __name__ == "__main__":
    main()
