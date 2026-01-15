from Common.db.database import Database
from Common.db.init_db import init_orders_schema
from Common.settings import DB_PATH
from Orders.api.ozon_api import get_unfulfilled_postings
from Common.logger import get_logger
from Orders.services.order_processor import save_to_files_server_response

logger = get_logger("Orders")


def main():
    try:
        logger.info("=== Запуск обработки заказов ===")

        db = Database(DB_PATH)
        init_orders_schema(db)

        response = get_unfulfilled_postings()     # пример
        save_to_files_server_response(response, db)

        logger.info("=== Обработка заказов завершена ===")

    except Exception as e:
        logger.exception(f"Критическая ошибка при работе Orders: {e}")


if __name__ == "__main__":
    main()
