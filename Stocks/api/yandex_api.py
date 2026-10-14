import time

from Common.http_utils import send_request_with_retries
from Common.logger import get_logger
from Common.settings import YANDEX_BUSINESS_ID, YANDEX_API_TOKEN, YANDEX_CAMPAIGN_ID
from Stocks.services.stock_processor import prepare_batches_yandex
from Stocks.services.update_result import UpdateResult, yandex_batch_succeeded
from Stocks.services.update_logging import log_update_result, response_reason
from Stocks.services.catalog_errors import CatalogLoadError

logger = get_logger(__name__)

def get_sku_from_yandex(limit=20, page_token=None, offer_ids=None):
    """
    Получает полный список товаров из кампании, обрабатывая все страницы.

    :param limit: Количество товаров на странице (по умолчанию 20).
    :param page_token: Токен следующей страницы для постраничного вывода.
    :param offer_ids: Список идентификаторов товаров для фильтрации (необязательно).
    :return: Список всех товаров.
    """
    url = f"https://api.partner.market.yandex.ru/v2/businesses/{YANDEX_BUSINESS_ID}/offer-mappings"
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
    page_number = 1
    seen_tokens = {page_token} if page_token else set()
    logger.info("Яндекс: начало загрузки каталога, размер страницы=%s", limit)
    while True:
        try:
            logger.info("Яндекс: запрос страницы=%s, уже загружено=%s", page_number, len(all_offers))
            data = send_request_with_retries(
                url=url, method="POST", headers=headers, body=body, params=dict(params),
            )
            if not isinstance(data, dict) or data.get("status") != "OK" or data.get("errors"):
                raise ValueError(response_reason(data, "status=OK без errors"))
            result = data.get("result")
            if not isinstance(result, dict):
                raise ValueError("некорректный result каталога")
            offers = result.get("offerMappings")
            paging = result.get("paging")
            if not isinstance(offers, list) or not isinstance(paging, dict):
                raise ValueError("отсутствуют или некорректны offerMappings/paging")
            for item in offers:
                offer = item.get("offer") if isinstance(item, dict) else None
                if not isinstance(offer, dict) or not isinstance(offer.get("offerId"), str) or not offer["offerId"]:
                    raise ValueError("товар каталога не содержит строковый offerId")

            next_page_token = paging.get("nextPageToken")
            if next_page_token is not None and not isinstance(next_page_token, str):
                raise ValueError("некорректный nextPageToken")
            if next_page_token and next_page_token in seen_tokens:
                raise ValueError("повторяющийся токен страницы; загрузка остановлена")

            all_offers.extend(offers)
            logger.info("Яндекс: страница=%s загружена, получено=%s, всего=%s",
                        page_number, len(offers), len(all_offers))
            if not next_page_token:
                logger.info("Яндекс: каталог загружен полностью, страниц=%s, товаров=%s",
                            page_number, len(all_offers))
                break
            seen_tokens.add(next_page_token)
            params['pageToken'] = next_page_token
            page_number += 1
        except Exception as e:
            error = CatalogLoadError(page_number, len(all_offers), str(e))
            logger.error("Яндекс: CATALOG_LOAD_FAILED, каталог не загружен полностью: %s", error)
            raise error from e

    return all_offers



def update_stocks_yandex(offers: list[dict]) -> UpdateResult:
    """
    Обновляет остатки на маркетплейсе Яндекс партиями.
    :param offers: список товаров [{"sku": str, "items": [{"count": int}]}]
    :return: количество подтвержденных обновлений и ошибок
    """
    url = f"https://api.partner.market.yandex.ru/v2/campaigns/{YANDEX_CAMPAIGN_ID}/offers/stocks"
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

