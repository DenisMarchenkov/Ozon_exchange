from Common.db.database import Database
from Common.db.init_db import init_prices_schema
from Prices.db_prices.prices_repository import PricesRepository
from Prices.services.prices_mailer import OzonPriceSyncMailer
from Prices.services.pricing_engine import MarkupReader, ProductReader, PricingEngine
from Prices.api.ozon_api import update_prices
from Prices.services.supplier_price_guard import SupplierPriceGuard, MarkupFileGuard
from Prices.settings_app.settings_prices import MARKUP_FILE
from Common.file_utils import copy_file_with_timestamp
from Common.settings import (API_TOKEN, CLIENT_ID, SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER, DB_PATH, SUPPLIER_ID,
                             RECIPIENT_MANAGERS)
from Common.logger import get_logger
from Stocks.api.ozon_api import get_sku_from_ozon

logger = get_logger("Prices")



def main():
    logger.info("=== Запуск обмена ценами ===")

    # -------------------------------------------------
    # ИНИЦИАЛИЗАЦИЯ
    # -------------------------------------------------
    db = Database(DB_PATH)
    init_prices_schema(db)

    repo_prices = PricesRepository(db)

    supplier_guard = SupplierPriceGuard(
        repo_prices,
        supplier_id=int(SUPPLIER_ID)
    )
    markup_guard = MarkupFileGuard(repo_prices)

    # -------------------------------------------------
    # 1. ПРОВЕРКА ИЗМЕНЕНИЙ ФАЙЛОВ
    # -------------------------------------------------

    # файл поставщика копируем всегда
    file_supplier = copy_file_with_timestamp(
        SUPPLIER_SOURCE_FILE,
        SUPPLIER_PRICE_FOLDER
    )

    supplier_result = supplier_guard.check(file_supplier)
    markup_result = markup_guard.check(MARKUP_FILE)

    if not supplier_result and not markup_result:
        logger.info("=== Пересчёт цен не требуется: входные файлы не изменились ===")
        return

    # лог причины пересчёта
    reasons = []
    if supplier_result:
        reasons.append("поставщик")
    if markup_result:
        reasons.append("наценки")

    logger.info("Причина пересчёта цен: %s", ", ".join(reasons))

    # -------------------------------------------------
    # 2. ОПРЕДЕЛЯЕМ АКТУАЛЬНЫЕ ID ФАЙЛОВ
    # -------------------------------------------------
    supplier_price_id = (
        supplier_result[1]
        if supplier_result
        else repo_prices.get_last_supplier_price_id(int(SUPPLIER_ID))
    )

    if supplier_price_id is None:
        logger.error("Невозможно выполнить пересчёт: нет файла поставщика")
        return

    markup_file_id = (
        markup_result[1]
        if markup_result
        else repo_prices.get_last_markup_file_id()
    )

    if markup_file_id is None:
        logger.error("Невозможно выполнить пересчёт: нет файла наценок")
        return

    # -------------------------------------------------
    # 3. ЧТЕНИЕ ДАННЫХ
    # -------------------------------------------------
    try:
        markup_reader = MarkupReader(MARKUP_FILE)
        markups = markup_reader.load_all()

        products_reader = ProductReader(file_supplier)
        products = products_reader.get_products()
    except Exception:
        logger.exception("Ошибка при чтении входных файлов")
        return

    # -------------------------------------------------
    # 4. РАСЧЁТ ЦЕН
    # -------------------------------------------------
    try:
        engine = PricingEngine(
            markups["global"],
            markups["manual"],
            repo_prices,
            supplier_price_id=supplier_price_id,
            markup_file_id=markup_file_id,
        )
        prices = engine.run(products)
    except Exception:
        logger.exception("Ошибка при расчёте цен")
        return

    # -------------------------------------------------
    # 5. СИНХРОНИЗАЦИЯ ДАННЫХ С ЛК ОЗОН
    # -------------------------------------------------
    sku_ozon = get_sku_from_ozon()
    # 5.1 все offer_id из Ozon
    ozon_offer_ids = {
        item.get('offer_id')
        for item in sku_ozon
        if item.get('offer_id')
    }

    # 5.2 все offer_id из прайса
    price_offer_ids = {
        item.get('offer_id')
        for item in prices
        if item.get('offer_id')
    }

    # 5.3 разницы
    missing_in_price = ozon_offer_ids - price_offer_ids
    missing_in_ozon = price_offer_ids - ozon_offer_ids

    # 5.4 фильтрация
    filtered_prices = [
        item for item in prices
        if item.get('offer_id') in ozon_offer_ids
    ]

    # 5.5 логирование
    logger.info(f"Всего товаров из прайса: {len(prices)}")
    logger.info(f"Всего товаров в Ozon: {len(sku_ozon)}")
    logger.info(f"Товаров для обновления цен Ozon: {len(filtered_prices)}")
    logger.info(f"Товаров которые есть в Ozon но нет в прайсе: {len(missing_in_price)}")
    logger.info(f"Товаров которые есть в прайсе но нет в Ozon: {len(missing_in_ozon)}")

    # -------------------------------------------------
    # 6. ОТПРАВКА ЦЕН В OZON
    # -------------------------------------------------
    try:
        update_prices(API_TOKEN, filtered_prices, CLIENT_ID)
        mailer = OzonPriceSyncMailer(
            missing_in_ozon=missing_in_ozon,
            missing_in_price=missing_in_price,
            filtered_prices=filtered_prices,
            to=RECIPIENT_MANAGERS
        )

        mailer.send()
    except Exception:
        logger.exception("Ошибка при отправке цен в Ozon")
        return

    logger.info("=== Обмен ценами успешно завершен ===")



if __name__ == "__main__":
    main()
