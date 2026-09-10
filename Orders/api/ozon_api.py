import datetime

from typing import Dict, Any
from Common.settings import CLIENT_ID, API_TOKEN
from Common.http_utils import send_request_with_retries

def get_unfulfilled_postings(status: str = "awaiting_packaging", limit: int = 1000) -> Dict[str, Any]:
    url = "https://api-seller.ozon.ru/v4/posting/fbs/unfulfilled/list"

    headers = {
        'Api-Key': API_TOKEN,
        'Accept': 'application/json',
        'Client-Id': CLIENT_ID
    }

    utc_now = datetime.datetime.now(datetime.timezone.utc)

    cutoff_from = (utc_now - datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cutoff_to = (utc_now + datetime.timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    data = {
        "filter": {
            "cutoff_from": cutoff_from,
            "cutoff_to": cutoff_to,
            "status": status,
        },
        "limit": limit,
        "with": {
            "analytics_data": True,
            "barcodes": True,
            "financial_data": True,
            "legal_info": True,
            "translit": False
        }
    }

    return send_request_with_retries(
        url=url,
        method="POST",
        headers=headers,
        body=data
    )
