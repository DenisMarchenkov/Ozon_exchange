from Common.db.database import Database
from Common.db.init_db import init_prices_schema
from Prices.db_prices.prices_repository import PricesRepository
from Prices.services.pricing_engine import MarkupReader, ProductReader, PricingEngine
from Prices.api.ozon_api import update_prices
from Prices.services.supplier_price_guard import SupplierPriceGuard, MarkupFileGuard
from Prices.settings_app.settings_prices import MARKUP_FILE
from Common.file_utils import copy_file_with_timestamp
from Common.settings import API_TOKEN, CLIENT_ID, SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER, DB_PATH, SUPPLIER_ID
from Common.logger import get_logger


logger = get_logger("Prices")

# def main():
#     logger.info("=== Запуск обмена ценами ===")
#
#     db = Database(DB_PATH)
#     init_prices_schema(db)
#
#     repo_prices = SupplierPriceHashRepository(db)
#
#
#     # ============================================================
#     # 1. СРАВНЕНИЕ ХЕШ-СУММ КОПИИ ФАЙЛА ПОСТАВЩИКА
#     # ============================================================
#     # file_supplier = copy_file_with_timestamp(SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER)
#     # guard = SupplierPriceGuard(repo_prices, int(SUPPLIER_ID))
#     # result = guard.check(file_supplier)
#     # if not result:
#     #     logger.info("=== Обмен ценами завершен ===")
#     #     return
#     #
#     # metadata, supplier_price_id = result
#
#     file_supplier = copy_file_with_timestamp(SUPPLIER_SOURCE_FILE, SUPPLIER_PRICE_FOLDER)
#
#     supplier_guard = SupplierPriceGuard(repo_prices, int(SUPPLIER_ID))
#     markup_guard = MarkupFileGuard(repo_prices)
#
#     supplier_result = supplier_guard.check(file_supplier)
#     markup_result = markup_guard.check(MARKUP_FILE)
#
#     if not supplier_result and not markup_result:
#         logger.info("=== Пересчёт цен не требуется ===")
#         return
#
#     supplier_price_id = (
#         supplier_result[1]
#         if supplier_result
#         else repo.get_last_supplier_price_id(SUPPLIER_ID)
#     )
#
#     markup_file_id = (
#         markup_result[1]
#         if markup_result
#         else repo.get_last_markup_file_id()
#     )
#
#     # ============================================================
#     # 2. ЧИТАЕМ ДАННЫЕ ИЗ ФАЙЛА
#     # ============================================================
#     markup_reader = MarkupReader(MARKUP_FILE)
#     markups = markup_reader.load_all()
#
#     products_reader = ProductReader(file_supplier)
#     products = products_reader.get_products()
#
#
#     # ============================================================
#     # 3. РАСЧЕТ ЦЕН
#     # ============================================================
#     engine = PricingEngine(markups["global"], markups["manual"],
#                            repo_prices, supplier_price_id=supplier_price_id)
#     prices = engine.run(products)
#
#     # ============================================================
#     # 4. ОБНОВЛЕНИЕ ЦЕН
#     # ============================================================
#     try:
#         update_prices(API_TOKEN, prices, CLIENT_ID)
#     except Exception:
#         logger.exception("Ошибка при отправке цен в Ozon")
#         return
#
#     logger.info("=== Обмен ценами завершен ===")


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
    # 5. ОТПРАВКА ЦЕН В OZON
    # -------------------------------------------------
    try:
        update_prices(API_TOKEN, prices, CLIENT_ID)
    except Exception:
        logger.exception("Ошибка при отправке цен в Ozon")
        return

    logger.info("=== Обмен ценами успешно завершен ===")



if __name__ == "__main__":
    main()
