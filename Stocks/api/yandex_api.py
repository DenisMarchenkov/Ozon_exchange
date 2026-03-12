import time
from pprint import pprint

import requests

from typing import Optional, Dict, Any

from Common.http_utils import send_request_with_retries
from Common.logger import get_logger
from Common.settings import YANDEX_BUSINESS_ID, YANDEX_API_TOKEN, YANDEX_CAMPAIGN_ID
from Stocks.services.stock_processor import prepare_batches_yandex

logger = get_logger(__name__)

def get_sku_from_yandex(limit=20, page_token=None, offer_ids=None):
    """
    Получает полный список товаров из кампании, обрабатывая все страницы.

    :param limit: Количество товаров на странице (по умолчанию 20).
    :param page_token: Токен следующей страницы для постраничного вывода.
    :param offer_ids: Список идентификаторов товаров для фильтрации (необязательно).
    :return: Список всех товаров.
    """
    url = f"https://api.partner.market.yandex.ru/businesses/{YANDEX_BUSINESS_ID}/offer-mappings"
    headers = {
        'Api-Key': f'{YANDEX_API_TOKEN}',
        'Accept': 'application/json',
        'X-Market-Integration': 'OrderGuard_V2'
    }

    params = {
        "limit": limit
    }

    if page_token:
        params["page_token"] = page_token

    body = {}
    if offer_ids:
        body["offerIds"] = offer_ids

    all_offers = []
    while True:
        try:
            response = requests.post(url, headers=headers, params=params, json=body)

            # Проверяем статус ответа
            if response.status_code != 200:
                logger.warning(f"Ошибка при запросе: {response.status_code}")
                break

            data = response.json()

            # Добавляем товары из текущего ответа в общий список
            all_offers.extend(data['result']['offerMappings'])

            # Получаем токен следующей страницы
            next_page_token = data['result']['paging'].get('nextPageToken')

            # Если токена нет — больше страниц нет, выходим из цикла
            if not next_page_token:
                break

            # Обновляем page_token для следующего запроса
            params['page_token'] = next_page_token

        except Exception as e:
            logger.error(f"Ошибка при получении списка товаров: {e}")
            break

    return all_offers



def update_stocks_yandex(offers: list[dict]) -> list[Optional[Dict[str, Any]]]:
    """
    Обновляет остатки на маркетплейс Ozon партиями.
    :param offers: список товаров [{"offerId": str, "qua": int}, ...]
    :return: список ответов API по партиям
    """
    url = f"https://api.partner.market.yandex.ru/campaigns/{YANDEX_CAMPAIGN_ID}/offers/stocks"
    headers = {
        'Api-Key': YANDEX_API_TOKEN,
        'Accept': 'application/json',
        'X-Market-Integration': 'OrderGuard_V2'
    }

    responses = []
    batches = prepare_batches_yandex(offers)
    pprint(batches)

    logger.info(f"Начинаем обновление остатков: {len(offers)} товаров ({len(batches)} партий)")

    for idx, batch in enumerate(batches, start=1):
        response = send_request_with_retries(url=url, method="PUT", headers=headers, body=batch)

        if response:
            logger.info(f"Партия {idx}/{len(batches)} успешно обновлена")
        else:
            logger.error(f"Ошибка при обновлении партии {idx}/{len(batches)}")

        responses.append(response)
        time.sleep(1)  # задержка между партиями

    logger.info("Обновление остатков завершено")
    return responses

