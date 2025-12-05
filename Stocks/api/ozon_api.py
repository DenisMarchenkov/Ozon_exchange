import time

from typing import Optional, Dict, Any
from Stocks.services.stock_processor import prepare_batches
from Common.http_utils import send_request_with_retries
from Common.settings import CLIENT_ID
from Common.logger import get_logger
logger = get_logger("Stocks")

def update_stocks(api_token: str, offers: list[dict]) -> list[Optional[Dict[str, Any]]]:
    """
    Обновляет остатки на маркетплейс Ozon партиями.
    :param api_token: API ключ
    :param offers: список товаров [{"offerId": str, "qua": int}, ...]
    :return: список ответов API по партиям
    """
    url = "https://api-seller.ozon.ru/v2/products/stocks"
    headers = {
        'Api-Key': api_token,
        'Accept': 'application/json',
        'Client-Id': CLIENT_ID
    }

    responses = []
    batches = prepare_batches(offers)

    logger.info(f"Начинаем обновление остатков: {len(offers)} товаров ({len(batches)} партий)")

    for idx, batch in enumerate(batches, start=1):
        response = send_request_with_retries(url=url, method="POST", headers=headers, body=batch)

        if response:
            logger.info(f"Партия {idx}/{len(batches)} успешно обновлена")
        else:
            logger.error(f"Ошибка при обновлении партии {idx}/{len(batches)}")

        responses.append(response)
        time.sleep(1)  # задержка между партиями

    logger.info("Обновление остатков завершено")
    return responses


def get_warehouse_id(api_token: str, client_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает список складов через Ozon API.
    """
    url = "https://api-seller.ozon.ru/v1/warehouse/list"
    headers = {
        'Api-Key': api_token,
        'Accept': 'application/json',
        'Client-Id': client_id
    }

    response = send_request_with_retries(url=url, headers=headers, method="POST")
    return response

