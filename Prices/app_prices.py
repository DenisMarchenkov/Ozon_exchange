from Prices.db_prices.prices_repository import SupplierPriceHashRepository
from Prices.services.pricing_engine import MarkupReader, ProductReader, PricingEngine
from Prices.api.ozon_api import update_prices
from Prices.services.supplier_price_guard import SupplierPriceGuard
from Prices.settings_app.settings_prices import MARKUP_FILE
from Common.file_utils import copy_file_with_timestamp
from Common.settings import API_TOKEN, CLIENT_ID, SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER, DB_PATH, SUPPLIER_ID
from Common.logger import get_logger


logger = get_logger("Prices")

def main():
    logger.info("=== Запуск обмена ценами ===")
    repo_prices = SupplierPriceHashRepository(DB_PATH)


    # ============================================================
    # 1. СРАВНЕНИЕ ХЕШ-СУММ КОПИИ ФАЙЛА ПОСТАВЩИКА
    # ============================================================
    file_supplier = copy_file_with_timestamp(SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER)
    guard = SupplierPriceGuard(repo_prices, int(SUPPLIER_ID))
    result = guard.check(file_supplier)
    if not result:
        logger.info("=== Обмен ценами завершен ===")
        return

    metadata, supplier_price_id = result

    # ============================================================
    # 2. ЧИТАЕМ ДАННЫЕ ИЗ ФАЙЛА
    # ============================================================
    markup_reader = MarkupReader(MARKUP_FILE)
    markups = markup_reader.load_all()

    products_reader = ProductReader(file_supplier)
    products = products_reader.get_products()


    # ============================================================
    # 3. РАСЧЕТ ЦЕН
    # ============================================================
    engine = PricingEngine(markups["global"], markups["manual"],
                           repo_prices, supplier_price_id=supplier_price_id)
    prices = engine.run(products)

    # ============================================================
    # 4. ОБНОВЛЕНИЕ ЦЕН
    # ============================================================
    try:
        update_prices(API_TOKEN, prices, CLIENT_ID)
    except Exception:
        logger.exception("Ошибка при отправке цен в Ozon")
        return

    logger.info("=== Обмен ценами завершен ===")


if __name__ == "__main__":
    main()
