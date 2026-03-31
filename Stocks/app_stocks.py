from Stocks.api.yandex_api import get_sku_from_yandex, update_stocks_yandex
from Stocks.readers.excel_reader import prepare_offers_data
from Stocks.api.ozon_api import update_stocks, get_sku_from_ozon, update_promo_timer
from Stocks.db_stocks.stocks_repository import StocksRepository
from Common.file_utils import copy_file_with_timestamp
from Common.settings import SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER
from Common.logger import get_logger
from Stocks.settings_app.settings_stocks import ENABLE_OZON, ENABLE_YANDEX, ENABLE_PROMO_TIMER

logger = get_logger(__name__)
repo = StocksRepository()


def start_exchange_stock(file):
    """
    Основная функция запуска обмена товарными остатками.
    """
    logger.info("=== Запуск обмена товарными остатками ===")

    # --- 1. Подготовка прайса ---
    # Читаем файл поставщика и приводим к единому формату
    offers = prepare_offers_data(file)

    # --- 2. Получаем товары из маркетплейсов ---
    # Если маркет отключен — просто получаем пустой список
    sku_ozon = get_sku_from_ozon() if ENABLE_OZON else []
    sku_yandex = get_sku_from_yandex() if ENABLE_YANDEX else []

    # --- 3. Создаём индексы для быстрого поиска ---
    # Это сильно ускоряет работу при больших объемах
    offers_index = {o["offerId"]: o for o in offers}              # offerId -> offer
    ozon_index = {o["offer_id"]: o for o in sku_ozon}             # offer_id -> sku
    yandex_index = {o["offer"]["offerId"]: o for o in sku_yandex}  # offerId -> sku

    # Guard check: защита от пустого прайс-листа
    # Если файл пуст — прерываем, чтобы не обнулить весь склад
    if not offers_index:
        logger.critical("Пустой файл! Прерываем процесс.")
        return []

    # --- 4. Генерируем списки для обновления ---
    stocks_to_update = []
    stocks_to_update_yandex = []

    # =========================
    # --- 4a. OZON логика ---
    # =========================
    if ENABLE_OZON:

        # Товары, которые есть и в прайсе, и в Ozon → обновляем остатки
        for offer_id, offer in offers_index.items():
            if offer_id in ozon_index:
                stocks_to_update.append({
                    "offer_id": offer_id,
                    "product_id": ozon_index[offer_id]["product_id"],
                    "stock": offer["qua"]
                })

        # Товары, которые есть в Ozon, но отсутствуют в прайсе → ставим 0
        for offer_id, sku in ozon_index.items():
            if offer_id not in offers_index:
                #logger.info(f"Товары, которые есть в Ozon, но отсутствуют в прайсе: offer_id: {offer_id} product_id: {sku['product_id']}")
                stocks_to_update.append({
                    "offer_id": offer_id,
                    "product_id": sku["product_id"],
                    "stock": 0
                })

    # =========================
    # --- 4b. YANDEX логика ---
    # =========================
    if ENABLE_YANDEX:

        # Товары, которые есть и в прайсе, и в Yandex → обновляем остатки
        for offer_id, offer in offers_index.items():
            if offer_id in yandex_index:
                stocks_to_update_yandex.append({
                    "sku": offer_id,
                    "items": [{"count": offer["qua"]}]
                })

        # Товары, которые есть в Yandex, но отсутствуют в прайсе → ставим 0
        for offer_id in yandex_index:
            if offer_id not in offers_index:
                stocks_to_update_yandex.append({
                    "sku": offer_id,
                    "items": [{"count": 0}]
                })

    # --- 5. Логирование ---
    logger.info(f"Всего товаров из прайса: {len(offers_index)}")
    logger.info(f"Всего товаров в Ozon: {len(ozon_index)} | Товаров к обновлению: {len(stocks_to_update)}")
    logger.info(f"Всего товаров в Yandex: {len(yandex_index)} | Товаров к обновлению: {len(stocks_to_update_yandex)}")

    # =========================
    # --- 6. Отправка в OZON ---
    # =========================
    if ENABLE_OZON:
        log_id = repo.create_stock_update_session(
            total_file=len(offers_index),
            total_ozon=len(ozon_index),
            marketplace="OZON"
        )
        try:
            # Сохраняем историю перед отправкой
            repo.save_stock_history_bulk(log_id, stocks_to_update)

            # Отправляем остатки
            response = update_stocks(stocks_to_update)
            #logger.info(response)

            # Завершаем сессию
            repo.finish_stock_update_session(log_id, len(stocks_to_update), "SUCCESS")
        except Exception as e:
            logger.error(f"Ошибка Ozon: {e}")
            repo.finish_stock_update_session(log_id, 0, f"ERROR: {str(e)[:100]}")

    # =========================
    # --- 7. Отправка в YANDEX ---
    # =========================
    if ENABLE_YANDEX:
        log_id = repo.create_stock_update_session(
            total_file=len(offers_index),
            total_ozon=len(yandex_index),
            marketplace="YANDEX"
        )
        try:
            # Сохраняем историю
            repo.save_yandex_stock_history_bulk(log_id, stocks_to_update_yandex)

            # Отправляем остатки
            update_stocks_yandex(stocks_to_update_yandex)

            # Завершаем сессию
            repo.finish_stock_update_session(log_id, len(stocks_to_update_yandex), "SUCCESS")
        except Exception as e:
            logger.error(f"Ошибка Yandex: {e}")
            repo.finish_stock_update_session(log_id, 0, f"ERROR: {str(e)[:100]}")

    logger.info("=== Завершено ===")
    return stocks_to_update


def start_update_promo_timer(data):
    """
    Функция обновления таймера участия в промо-акциях
    """

    # Если промо отключено — сразу выходим
    if not ENABLE_PROMO_TIMER:
        logger.info("Промо отключено")
        return

    logger.info("=== Обновление промо  ===")

    # Убираем дубликаты product_id
    product_ids = list(set(item["product_id"] for item in data))

    if not product_ids:
        logger.info("Нет товаров")
        return

    # Создаем сессию логирования
    log_id = repo.create_promo_timer_session(len(product_ids))

    try:
        # Сохраняем историю
        repo.save_promo_timer_history_bulk(log_id, product_ids)

        # Обновляем таймер в Ozon
        update_promo_timer(product_ids, batch_size=500)

        # Успешное завершение
        repo.finish_promo_timer_session(log_id, "SUCCESS")
    except Exception as e:
        logger.error(f"Ошибка промо: {e}")
        repo.finish_promo_timer_session(log_id, f"ERROR: {str(e)[:100]}")

    logger.info("=== Промо завершено ===")


def main():
    """
    Точка входа:
    1. Копируем файл поставщика
    2. Обновляем остатки
    3. Обновляем промо
    """

    file_supplier = copy_file_with_timestamp(SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER)

    stocks_to_update = start_exchange_stock(file_supplier)

    start_update_promo_timer(stocks_to_update)


if __name__ == "__main__":
    main()
