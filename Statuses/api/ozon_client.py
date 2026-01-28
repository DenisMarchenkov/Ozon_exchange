import asyncio
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

OZON_FBS_GET_URL = "https://api-seller.ozon.ru/v3/posting/fbs/get"


class OzonClient:
    def __init__(
        self,
        headers: dict,
        max_concurrent_requests: int = 5,
        timeout: int = 15,
        retries: int = 5,
        base_delay: int = 2,
    ):
        self.headers = headers
        self.timeout = timeout
        self.retries = retries
        self.base_delay = base_delay
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _fetch_posting(
        self,
        session: aiohttp.ClientSession,
        posting_number: str,
    ) -> dict:
        data = {"posting_number": posting_number}

        for attempt in range(1, self.retries + 1):
            try:
                async with session.post(
                    OZON_FBS_GET_URL,
                    json=data,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response.raise_for_status()
                    payload = await response.json()
                    result = payload.get("result", {})

                    return {
                        "posting_number": result.get("posting_number"),
                        "status": result.get("status"),
                        "substatus": result.get("substatus"),
                        "cancel_reason": result.get("cancellation", {}).get("cancel_reason"),
                    }

            except Exception as e:
                logger.warning(
                    "[%s] OZON request error (attempt %s/%s): %s",
                    posting_number,
                    attempt,
                    self.retries,
                    e,
                )

                if attempt < self.retries:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

        return {
            "posting_number": posting_number,
            "status": None,
            "substatus": None,
            "cancel_reason": None,
            "error": "max retries exceeded",
        }

    async def get_posting_status(
        self,
        session: aiohttp.ClientSession,
        posting_number: str,
    ) -> dict:
        async with self.semaphore:
            return await self._fetch_posting(session, posting_number)

    async def get_many(self, posting_numbers: list[str]) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.get_posting_status(session, posting_number)
                for posting_number in posting_numbers
            ]
            return await asyncio.gather(*tasks)
