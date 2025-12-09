from Prices.services.pricing_engine import MarkupReader, ProductReader, PricingEngine
from Prices.api.ozon_api import update_prices
from Prices.settings_app.settings_prices import MARKUP_FILE
from Common.file_utils import copy_file_with_timestamp
from Common.settings import API_TOKEN, CLIENT_ID, SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER
from Common.logger import get_logger
logger = get_logger("Prices")

def start_exchange_price(file):
    logger.info("=== Запуск обмена ценами ===")

    markup_reader = MarkupReader(MARKUP_FILE)
    markups = markup_reader.load_all()

    products_reader = ProductReader(file)
    products = products_reader.get_products()

    engine = PricingEngine(markups["global"], markups["manual"])
    prices = engine.run(products)

    update_prices(API_TOKEN, prices, CLIENT_ID)
    logger.info("=== Обмен ценами завершен ===")


if __name__ == "__main__":
    file_supplier = copy_file_with_timestamp(SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER)
    start_exchange_price(file_supplier)
