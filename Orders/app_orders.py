from api.ozon_api import get_unfulfilled_postings
from services.order_processor import save_to_files_server_response
from Common.logger import get_logger
from Common.db import init_db
logger = get_logger("Orders")


def main():
    try:
        init_db()
        logger.info("База данных инициализирована")

        response = get_unfulfilled_postings()     # пример
        save_to_files_server_response(response)

        logger.info("Обработка заказов завершена")

    except Exception as e:
        logger.exception(f"Критическая ошибка при работе Orders: {e}")


if __name__ == "__main__":
    main()