from api.ozon_api import get_unfulfilled_postings
from services.order_processor import save_to_files_server_response
from Common.logger import get_logger
logger = get_logger("Orders")

def main():
    logger.info("=== Запуск получения заказов ===")

    try:
        response = get_unfulfilled_postings()
    except Exception as e:
        logger.exception(f"Ошибка запроса к Ozon API - {e}")
        return

    save_to_files_server_response(response)
    logger.info("=== Получение заказов завершено ===")


if __name__ == "__main__":
    main()