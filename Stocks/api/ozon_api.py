import time

from typing import Optional, Dict, Any
from Stocks.services.stock_processor import prepare_batches
from Common.http_utils import send_request_with_retries
from Common.settings import CLIENT_ID, API_TOKEN
from Common.logger import get_logger
logger = get_logger(__name__)

def update_stocks(offers: list[dict]) -> list[Optional[Dict[str, Any]]]:
    """
    Обновляет остатки на маркетплейс Ozon партиями.
    :param offers: список товаров [{"offerId": str, "qua": int}, ...]
    :return: список ответов API по партиям
    """
    url = "https://api-seller.ozon.ru/v2/products/stocks"
    headers = {
        'Api-Key': API_TOKEN,
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



def get_sku_from_ozon():
    url = "https://api-seller.ozon.ru/v3/product/list"

    headers = {
        "Api-Key": API_TOKEN,
        "Client-Id": CLIENT_ID,
        "Content-Type": "application/json"
    }

    all_items = []
    last_id = ""

    while True:
        body = {
            "filter": {
                "visibility": "ALL"
            },
            "last_id": last_id,
            "limit": 1000
        }

        response = send_request_with_retries(
            url=url,
            headers=headers,
            method="POST",
            body=body
        )

        items = response["result"]["items"]
        last_id = response["result"]["last_id"]

        all_items.extend(items)

        # если last_id пустой — значит это последняя страница
        if not last_id:
            break

    return all_items


def update_promo_timer(prod_ids, batch_size=100):
    """
    Запускает обновление таймера промо-акций (актуальности цены) для товаров Ozon партиями.
    """

    url = "https://api-seller.ozon.ru/v1/product/action/timer/update"

    headers = {
        "Api-Key": API_TOKEN,
        "Client-Id": CLIENT_ID,
        "Content-Type": "application/json"
    }

    responses = []

    # разбиваем на партии
    for i in range(0, len(prod_ids), batch_size):
        batch = prod_ids[i:i + batch_size]

        body = {
            "product_ids": batch
        }

        response = send_request_with_retries(
            url=url,
            headers=headers,
            method="POST",
            body=body
        )

        responses.append(response)

        logger.info(f"Отправлена партия {i//batch_size + 1}, товаров: {len(batch)}")

        time.sleep(1)  # чтобы не ловить rate limit

    return responses
