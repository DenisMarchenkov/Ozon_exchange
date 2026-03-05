from Stocks.readers.excel_reader import prepare_offers_data
from Stocks.api.ozon_api import update_stocks, get_sku_from_ozon, update_promo_timer
from Stocks.db_stocks.stocks_repository import StocksRepository
from Common.file_utils import copy_file_with_timestamp
from Common.settings import SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER
from Common.logger import get_logger
logger = get_logger(__name__)

repo = StocksRepository()


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
    
    # Guard check: защита от пустого прайс-листа (предотвращение обнуления всего склада)
    if not offers_index:
        logger.critical("Внимание! В файле не найдено товаров или он пуст! Прерываем процесс для защиты от обнуления остатков.")
        return []

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

    # --- 6. Запись в БД и Отправка в Ozon ---
    log_id = repo.create_stock_update_session(total_file=len(offers_index), total_ozon=len(ozon_index))
    
    try:
        # Сохраняем историю в БД перед отправкой
        repo.save_stock_history_bulk(log_id, stocks_to_update)
        
        # Отправка в Ozon
        update_stocks(stocks_to_update)
        
        repo.finish_stock_update_session(log_id, items_updated=len(stocks_to_update), status="SUCCESS")
    except Exception as e:
        logger.error(f"Ошибка при обновлении остатков: {e}")
        repo.finish_stock_update_session(log_id, items_updated=0, status=f"ERROR: {str(e)[:100]}")

    logger.info("=== Обмен товарными остатками завершен ===")
    return stocks_to_update


def start_update_promo_timer(data):
    """
    Функция обновления таймера актуальности участия в промо-акциях
    """
    logger.info("=== Запуск обновления таймера промо-акций ===")

    # --- 1. Подготовка данных (убираем дубликаты product_id) ---
    product_ids = list(set(item["product_id"] for item in data))
    
    if not product_ids:
        logger.info("Нет товаров для обновления таймера.")
        return

    # --- 2. Запись в БД и Обновление таймера ---
    log_id = repo.create_promo_timer_session(total_items=len(product_ids))
    
    try:
        # Сохраняем историю в БД
        repo.save_promo_timer_history_bulk(log_id, product_ids)
        
        # Обновление таймера в Ozon
        update_promo_timer(product_ids, batch_size=500)
        
        repo.finish_promo_timer_session(log_id, status="SUCCESS")
    except Exception as e:
        logger.error(f"Ошибка при обновлении таймера промо: {e}")
        repo.finish_promo_timer_session(log_id, status=f"ERROR: {str(e)[:100]}")

    logger.info("=== Обновление таймера промо-акций завершено ===")

def main():
    file_supplier = copy_file_with_timestamp(SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER)
    stocks_to_update = start_exchange_stock_ozon(file_supplier)
    start_update_promo_timer(stocks_to_update)


if __name__ == "__main__":
    main()
