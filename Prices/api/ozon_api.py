import time

from Prices.services.pricing_engine import prepare_batches
from Common.http_utils import send_request_with_retries


def update_prices(api_token: str, prices: list, client_id: str) -> list:
    url = "https://api-seller.ozon.ru/v1/product/import/prices"
    headers = {
        'Api-Key': api_token,
        'Accept': 'application/json',
        'Client-Id': client_id,
        'Content-Type': 'application/json',
    }

    responses = []
    batches = prepare_batches(prices)

    for batch in batches:
        payload = {
            "prices": batch
        }

        response = send_request_with_retries(
            url,
            "POST",
            headers,
            body=payload
        )

        responses.append(response)
        time.sleep(1)

    return responses
