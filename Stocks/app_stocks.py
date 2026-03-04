from Stocks.readers.excel_reader import prepare_offers_data
from Stocks.api.ozon_api import update_stocks, get_sku_from_ozon, set_update_timer_min_price
from Common.file_utils import copy_file_with_timestamp
from Common.settings import API_TOKEN, SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER, CLIENT_ID
from Common.logger import get_logger
logger = get_logger(__name__)


def start_exchange_stock_ozon(file):
    """
    Основная функция запуска обмена товарными остатками.
    """
    logger.info("=== Запуск обмена товарными остатками ===")

    # --- 1. Подготовка прайса ---
    offers = prepare_offers_data(file)

    # --- 2. Получаем товары из Ozon ---
    sku_ozon = get_sku_from_ozon()

    # --- 3. Создаём индексы для быстрого поиска ---
    offers_index = {o["offerId"]: o for o in offers}      # offerId -> offer
    ozon_index = {o["offer_id"]: o for o in sku_ozon}     # offer_id -> sku


    # --- 4. Генерируем список для загрузки ---
    stocks_to_update = []

    # 4a. Товары, которые есть и в Ozon, и в прайсе → обновляем остаток
    for offer_id, offer in offers_index.items():
        if offer_id in ozon_index:
            stocks_to_update.append({
                "offer_id": offer_id,
                "product_id": ozon_index[offer_id]["product_id"],
                "stock": offer["qua"]
            })

    # 4b. Товары, которые есть в Ozon, но нет в прайсе → ставим 0
    for offer_id, sku in ozon_index.items():
        if offer_id not in offers_index:
            stocks_to_update.append({
                "offer_id": offer_id,
                "product_id": sku["product_id"],
                "stock": 0
            })

    # --- 5. Логируем для проверки ---
    logger.info(f"Всего товаров из прайса: {len(offers_index)}")
    logger.info(f"Всего товаров в Ozon: {len(ozon_index)}")
    logger.info(f"Товаров для обновления остатков: {len(stocks_to_update)}")


    # --- 6. Отправка в Ozon ---
    update_stocks(stocks_to_update)

    logger.info("=== Обмен товарными остатками завершен ===")
    return stocks_to_update


def start_update_timer_min_price(data):
    """
    Функция обновления таймера актуальности минимальной цены
    """
    logger.info("=== Запуск обновления таймера минимальной цены ===")

    # --- 1. Подготовка данных ---
    product_ids = [item["product_id"] for item in data]

    # --- 2. Обновление таймера ---
    set_update_timer_min_price(product_ids, batch_size=500)

    logger.info("=== Обновление таймера минимальной цены завершено ===")

def main():
    file_supplier = copy_file_with_timestamp(SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER)
    stocks_to_update = start_exchange_stock_ozon(file_supplier)
    start_update_timer_min_price(stocks_to_update)


if __name__ == "__main__":
    main()
