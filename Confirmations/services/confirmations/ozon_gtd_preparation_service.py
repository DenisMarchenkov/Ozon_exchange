from typing import Set, Tuple, Dict

from Common.settings import CLIENT_ID, API_TOKEN
from Common.http_utils import send_request_with_retries

from Common.logger import get_logger
logger = get_logger(__name__)


class GtdRepository:
    """
    Репозиторий для работы с GTD товаров.
    Использует объект Database вместо прямого подключения к SQLite.
    """
    def __init__(self, db):
        self.db = db

    def load_bulk(
        self,
        keys: Set[Tuple[str, int]]
    ) -> Dict[Tuple[str, int], str | None]:
        """
        Загружает GTD для списка (posting_number, product_id)
        """
        if not keys:
            return {}

        # SQLite не поддерживает (a,b) IN ((?,?), ...), делаем через OR
        placeholders = " OR ".join("(o.posting_number=? AND oi.product_id=?)" for _ in keys)
        params = [v for k in keys for v in k]

        query = f"""
            SELECT o.posting_number,
                   oi.product_id,
                   ci.gtd
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            LEFT JOIN confirmation_items ci ON oi.offer_id = ci.sku_art
            WHERE {placeholders}
        """

        with self.db.connect() as conn:
            #conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query, params)
            result = {
                (r["posting_number"], r["product_id"]): r["gtd"]
                for r in cur.fetchall()
            }

        return result


class OzonGtdPreparationService:

    def __init__(self, gtd_repo):
        self.gtd_repo = gtd_repo

    def prepare(self, ship_not_available: dict) -> list[dict]:
        exemplars = self._extract_exemplars(ship_not_available)

        keys = {
            (e["posting_number"], e["product_id"])
            for e in exemplars
        }

        gtd_map = self.gtd_repo.load_bulk(keys)

        return self._build_payload(exemplars, gtd_map)


    def _extract_exemplars(self, ship_data: dict) -> list[dict]:
        seen = set()
        result = []

        for posting in ship_data.values():
            posting_number = posting.get("posting_number")
            if not posting_number:
                continue

            for product in posting.get("products", []):
                product_id = product.get("product_id")
                if not product_id:
                    continue

                for exemplar in product.get("exemplars", []):
                    exemplar_id = exemplar.get("exemplar_id")
                    if not exemplar_id:
                        continue

                    key = (posting_number, product_id, exemplar_id)
                    if key in seen:
                        continue

                    seen.add(key)

                    result.append({
                        "posting_number": posting_number,
                        "product_id": product_id,
                        "exemplar_id": exemplar_id,
                    })

        return result


    def _build_payload(
        self,
        exemplars: list[dict],
        gtd_map: dict
    ) -> list[dict]:
        postings = {}

        for e in exemplars:
            gtd = gtd_map.get((e["posting_number"], e["product_id"]))
            if not gtd or str(gtd).lower() == "nan":
                logger.info(
                    "Пропуск exemplar: posting=%s product=%s exemplar=%s — GTD отсутствует",
                    e["posting_number"],
                    e["product_id"],
                    e["exemplar_id"],
                )
                continue

            posting = postings.setdefault(
                e["posting_number"],
                {"posting_number": e["posting_number"], "products": {}}
            )

            product = posting["products"].setdefault(
                e["product_id"],
                {"product_id": e["product_id"], "exemplars": []}
            )

            product["exemplars"].append({
                "exemplar_id": e["exemplar_id"],
                "gtd": gtd,
            })

        return [
            {
                "posting_number": p["posting_number"],
                "products": list(p["products"].values())
            }
            for p in postings.values()
        ]



class OzonGtdUpdater:
    """
    Минимальный API-клиент.
    """

    URL_STATUS = (
        "https://api-seller.ozon.ru/v6/fbs/posting/product/exemplar/set"
    )

    def __init__(self):
        self.headers = {
            "Client-Id": CLIENT_ID,
            "Api-Key": API_TOKEN,
            "Content-Type": "application/json",
        }

    def update_gtd(self, payload) -> dict:
        return send_request_with_retries(
            url=self.URL_STATUS,
            method="POST",
            headers=self.headers,
            body=payload,
        )