import time

from typing import Optional, Dict, Any
from Stocks.services.stock_processor import prepare_batches
from Stocks.services.update_result import UpdateResult, confirmed_ozon_stocks, promo_batch_succeeded
from Stocks.services.update_logging import log_ozon_failures, log_update_result, response_reason
from Stocks.services.catalog_errors import CatalogLoadError
from Common.http_utils import send_request_with_retries
from Common.settings import CLIENT_ID, API_TOKEN
from Common.logger import get_logger
logger = get_logger(__name__)

def update_stocks(offers: list[dict]) -> UpdateResult:
    """
    Обновляет остатки на маркетплейс Ozon партиями.
    :param offers: список товаров [{"offer_id": str, "stock": int}, ...]
    :return: количество подтвержденных обновлений и ошибок
    """
    url = "https://api-seller.ozon.ru/v2/products/stocks"
    headers = {
        'Api-Key': API_TOKEN,
        'Accept': 'application/json',
        'Client-Id': CLIENT_ID
    }

    result = UpdateResult()
    batches = prepare_batches(offers)

    logger.info(f"Начинаем обновление остатков: {len(offers)} товаров ({len(batches)} партий)")

    for idx, batch in enumerate(batches, start=1):
        response = None
        try:
            response = send_request_with_retries(url=url, method="POST", headers=headers, body=batch)
            updated = confirmed_ozon_stocks(batch, response)
        except Exception:
            logger.exception("Ошибка при обновлении партии %s/%s", idx, len(batches))
            updated = 0

        failed = len(batch["stocks"]) - updated
        result.updated += updated
        result.failed += failed
        logger.info("Партия %s/%s: подтверждено %s, не подтверждено %s", idx, len(batches), updated, failed)
        if failed:
            log_ozon_failures(logger, batch, response, idx)
        time.sleep(1)  # задержка между партиями

    log_update_result(logger, "Обновление остатков Ozon", result)
    return result


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
    page_number = 1
    seen_tokens = set()
    logger.info("Ozon: начало загрузки каталога, размер страницы=1000")

    while True:
        body = {
            "filter": {
                "visibility": "ALL"
            },
            "last_id": last_id,
            "limit": 1000
        }

        try:
            logger.info("Ozon: запрос страницы=%s, уже загружено=%s", page_number, len(all_items))
            response = send_request_with_retries(
                url=url, headers=headers, method="POST", body=body
            )
            if not isinstance(response, dict) or response.get("errors") or response.get("code"):
                raise ValueError(response_reason(response, "result каталога"))
            result = response.get("result")
            if not isinstance(result, dict):
                raise ValueError("некорректный result каталога")
            items = result.get("items")
            next_id = result.get("last_id")
            if not isinstance(items, list) or not isinstance(next_id, str):
                raise ValueError("отсутствуют или некорректны items/last_id")
            for item in items:
                if (not isinstance(item, dict)
                        or not isinstance(item.get("offer_id"), str) or not item["offer_id"]
                        or type(item.get("product_id")) is not int or item["product_id"] <= 0):
                    raise ValueError("товар каталога не содержит корректные offer_id/product_id")
            if items and next_id and next_id in seen_tokens:
                raise ValueError("повторяющийся токен страницы; загрузка остановлена")

            all_items.extend(items)
            logger.info("Ozon: страница=%s загружена, получено=%s, всего=%s",
                        page_number, len(items), len(all_items))
            if not items or not next_id:
                logger.info("Ozon: каталог загружен полностью, страниц=%s, товаров=%s",
                            page_number, len(all_items))
                break
            seen_tokens.add(next_id)
            last_id = next_id
            page_number += 1
        except Exception as e:
            error = CatalogLoadError(page_number, len(all_items), str(e))
            logger.error("Ozon: CATALOG_LOAD_FAILED, каталог не загружен полностью: %s", error)
            raise error from e

    return all_items


def update_promo_timer(prod_ids, batch_size=100) -> UpdateResult:
    """
    Запускает обновление таймера промо-акций (актуальности цены) для товаров Ozon партиями.
    """

    url = "https://api-seller.ozon.ru/v1/product/action/timer/update"

    headers = {
        "Api-Key": API_TOKEN,
        "Client-Id": CLIENT_ID,
        "Content-Type": "application/json"
    }

    if batch_size <= 0:
        raise ValueError("batch_size должен быть положительным")
    result = UpdateResult()
    logger.info("Обновление промо Ozon: товаров=%s, размер партии=%s", len(prod_ids), batch_size)

    # разбиваем на партии
    for i in range(0, len(prod_ids), batch_size):
        batch = prod_ids[i:i + batch_size]

        body = {
            "product_ids": batch
        }

        response = None
        try:
            response = send_request_with_retries(
                url=url, headers=headers, method="POST", body=body
            )
            success = promo_batch_succeeded(response)
        except Exception:
            logger.exception("Ошибка обновления промо, партия %s", i // batch_size + 1)
            success = False

        if success:
            result.updated += len(batch)
            logger.info("Промо Ozon: партия %s, подтверждено %s товаров", i // batch_size + 1, len(batch))
        else:
            result.failed += len(batch)
            logger.error(
                "Промо Ozon: партия %s, product_ids=%s; причина: %s",
                i // batch_size + 1, batch, response_reason(response, "result=true"),
            )

        time.sleep(1)  # чтобы не ловить rate limit

    log_update_result(logger, "Обновление промо Ozon", result)
    return result


def get_marked_products(
        offer_ids: list[str],
) -> list[str]:
    """
    Возвращает offer_id товаров, у которых
    установлен признак обязательной маркировки.

    :param offer_ids: список артикулов Ozon (offer_id)
    """

    url = "https://api-seller.ozon.ru/v4/product/info/attributes"
    MARKING_ATTRIBUTE_ID = 23536 # нашел в документации озона

    headers = {
        "Client-Id": CLIENT_ID,
        "Api-Key": API_TOKEN,
        "Content-Type": "application/json",
    }

    result: list[str] = []
    last_id = ""

    while True:
        body = {
            "filter": {
                "offer_id": offer_ids,
                "visibility": "ALL",
            },
            "limit": 100,
            "last_id": last_id,
        }

        response = send_request_with_retries(
            url=url,
            headers=headers,
            method="POST",
            body=body
        )

        last_id = response.get("last_id")
        for product in response.get("result", []):

            for attribute in product.get("attributes", []):
                if attribute.get("id") != MARKING_ATTRIBUTE_ID:
                    continue

                for value in attribute.get("values", []):
                    if value.get("value", "").lower() == "true":
                        result.append(product["offer_id"])
                        break

                break

        last_id = response.get("last_id", "")

        if not last_id:
            break

    return result
