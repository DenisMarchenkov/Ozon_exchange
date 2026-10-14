import importlib.util
import logging
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch


def load_yandex_api(post):
    """Load the real API module without credentials or network dependencies."""
    dependencies = {
        "requests": {"post": post},
        "Common.http_utils": {"send_request_with_retries": Mock()},
        "Common.logger": {"get_logger": logging.getLogger},
        "Common.settings": {
            "YANDEX_BUSINESS_ID": "test-business",
            "YANDEX_API_TOKEN": "test-token",
            "YANDEX_CAMPAIGN_ID": "test-campaign",
        },
        "Stocks.services.stock_processor": {"prepare_batches_yandex": Mock()},
    }
    modules = {}
    for name, attributes in dependencies.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module

    path = Path(__file__).resolve().parents[1] / "Stocks/api/yandex_api.py"
    spec = importlib.util.spec_from_file_location("stocks_yandex_under_test", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict("sys.modules", modules):
        spec.loader.exec_module(module)
    return module


def page(offer_id, next_token=None):
    return Mock(
        status_code=200,
        json=Mock(return_value={
            "result": {
                "offerMappings": [{"offer": {"offerId": offer_id}}],
                "paging": {"nextPageToken": next_token},
            }
        }),
    )


class YandexPaginationTests(unittest.TestCase):
    def test_reads_next_page_and_stops_on_last_page(self):
        observed_params = []

        def post(url, **kwargs):
            params = dict(kwargs["params"])
            observed_params.append(params)
            # Behave like an API that ignores unknown query parameters.
            if params.get("pageToken") == "second-page":
                return page("B")
            if len(observed_params) > 2:
                raise RuntimeError("Repeated first page")
            return page("A", "second-page")

        api = load_yandex_api(post)
        offers = api.get_sku_from_yandex(limit=20)

        self.assertEqual(offers, [
            {"offer": {"offerId": "A"}},
            {"offer": {"offerId": "B"}},
        ])
        self.assertEqual(observed_params, [
            {"limit": 20},
            {"limit": 20, "pageToken": "second-page"},
        ])

    def test_passes_initial_page_token(self):
        post = Mock(return_value=page("B"))
        api = load_yandex_api(post)

        self.assertEqual(api.get_sku_from_yandex(page_token="start-page"), [
            {"offer": {"offerId": "B"}},
        ])
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["params"], {
            "limit": 20, "pageToken": "start-page",
        })


if __name__ == "__main__":
    unittest.main()
