import time
import requests

from Common.http_utils import send_request_with_retries
from Common.logger import get_logger
from Common.settings import YANDEX_BUSINESS_ID, YANDEX_API_TOKEN, YANDEX_CAMPAIGN_ID
from Stocks.services.stock_processor import prepare_batches_yandex
from Stocks.services.update_result import UpdateResult, yandex_batch_succeeded
from Stocks.services.update_logging import log_update_result, response_reason

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
        params["pageToken"] = page_token

    body = {}
    if offer_ids:
        body["offerIds"] = offer_ids

    all_offers = []
    while True:
        try:
            response = requests.post(url, headers=headers, params=params, json=body, timeout=(5,30))

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
            params['pageToken'] = next_page_token

        except Exception as e:
            logger.error(f"Ошибка при получении списка товаров: {e}")
            break

    return all_offers



def update_stocks_yandex(offers: list[dict]) -> UpdateResult:
    """
    Обновляет остатки на маркетплейсе Яндекс партиями.
    :param offers: список товаров [{"sku": str, "items": [{"count": int}]}]
    :return: количество подтвержденных обновлений и ошибок
    """
    url = f"https://api.partner.market.yandex.ru/campaigns/{YANDEX_CAMPAIGN_ID}/offers/stocks"
    headers = {
        'Api-Key': YANDEX_API_TOKEN,
        'Accept': 'application/json',
        'X-Market-Integration': 'OrderGuard_V2'
    }

    result = UpdateResult()
    batches = prepare_batches_yandex(offers)

    logger.info(f"Начинаем обновление остатков: {len(offers)} товаров ({len(batches)} партий)")

    for idx, batch in enumerate(batches, start=1):
        response = None
        try:
            response = send_request_with_retries(url=url, method="PUT", headers=headers, body=batch)
            success = yandex_batch_succeeded(response)
        except Exception:
            logger.exception("Ошибка при обновлении партии %s/%s", idx, len(batches))
            success = False

        if success:
            result.updated += len(batch["skus"])
            logger.info("Партия %s/%s успешно обновлена", idx, len(batches))
        else:
            result.failed += len(batch["skus"])
            logger.error(
                "Яндекс: партия %s/%s, не подтверждено %s товаров, skus=%s; причина: %s",
                idx, len(batches), len(batch["skus"]),
                [item["sku"] for item in batch["skus"]],
                response_reason(response, "status=OK без errors"),
            )
        time.sleep(1)  # задержка между партиями

    log_update_result(logger, "Обновление остатков Яндекс", result)
    return result

