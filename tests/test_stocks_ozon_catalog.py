import unittest

from Stocks.services.catalog_errors import CatalogLoadError
from test_stocks_update_results import load_api


def page(offer_id=None, last_id=""):
    items = [] if offer_id is None else [{"offer_id": offer_id, "product_id": 1}]
    return {"result": {"items": items, "last_id": last_id}}


class OzonCatalogTests(unittest.TestCase):
    def test_reads_complete_catalog_with_cursor(self):
        api, send = load_api("Stocks/api/ozon_api.py", [page("A", "next"), page("B")])
        with self.assertLogs(api.logger, level="INFO") as logs:
            items = api.get_sku_from_ozon()
        self.assertEqual([item["offer_id"] for item in items], ["A", "B"])
        self.assertEqual([call.kwargs["body"]["last_id"] for call in send.call_args_list], ["", "next"])
        self.assertIn("каталог загружен полностью", "\n".join(logs.output))

    def test_partial_catalog_is_not_returned_after_failed_page(self):
        for failure in [None, RuntimeError("network error")]:
            with self.subTest(failure=failure):
                api, _ = load_api("Stocks/api/ozon_api.py", [page("A", "next"), failure])
                with self.assertRaises(CatalogLoadError) as raised:
                    api.get_sku_from_ozon()
                self.assertEqual(raised.exception.page_number, 2)
                self.assertEqual(raised.exception.loaded_count, 1)

    def test_malformed_response_fails_closed(self):
        for response in [
            {}, {"result": True}, {"result": {"items": [], "last_id": None}},
            {"result": {"items": [{}], "last_id": ""}},
            {"result": {"items": [{"offer_id": "A", "product_id": None}], "last_id": ""}},
            {"errors": [{"code": "denied"}]},
        ]:
            with self.subTest(response=response):
                api, _ = load_api("Stocks/api/ozon_api.py", [response])
                with self.assertRaises(CatalogLoadError):
                    api.get_sku_from_ozon()

    def test_repeated_cursor_stops_loading(self):
        api, send = load_api("Stocks/api/ozon_api.py", [page("A", "next"), page("B", "next")])
        with self.assertRaises(CatalogLoadError):
            api.get_sku_from_ozon()
        self.assertEqual(send.call_count, 2)

    def test_empty_last_page_ends_loading_even_with_previous_cursor(self):
        api, send = load_api("Stocks/api/ozon_api.py", [page("A", "next"), page(last_id="next")])
        self.assertEqual(api.get_sku_from_ozon(), [{"offer_id": "A", "product_id": 1}])
        self.assertEqual(send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
