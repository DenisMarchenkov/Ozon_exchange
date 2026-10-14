import importlib.util
import logging
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


class RequestFailure(Exception):
    pass


def response(data, status=200, headers=None):
    return Mock(status_code=status, headers=headers or {}, text="test error",
                json=Mock(return_value=data))


def load_http(responses):
    request = Mock(side_effect=responses)
    modules = {}
    dependencies = {
        "requests": {
            "request": request, "Response": Mock,
            "exceptions": SimpleNamespace(RequestException=RequestFailure),
        },
        "Common.settings": {"DEV_MODE": False},
        "Common.logger": {"get_logger": logging.getLogger},
        "Common.file_utils": {"get_fake_data": Mock()},
        "time": {"sleep": Mock()},
    }
    for name, attributes in dependencies.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module
    path = Path(__file__).resolve().parents[1] / "Common/http_utils.py"
    spec = importlib.util.spec_from_file_location("http_under_test", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict("sys.modules", modules):
        spec.loader.exec_module(module)
    return module, request


class HttpRetriesTests(unittest.TestCase):
    def test_promo_accepts_empty_json_from_http_200(self):
        from test_stocks_update_results import load_api
        from Stocks.services.update_result import UpdateResult
        http, request = load_http([response({})])
        api, _ = load_api("Stocks/api/ozon_api.py", [])
        api.send_request_with_retries = http.send_request_with_retries
        self.assertEqual(api.update_promo_timer([1, 2]), UpdateResult(updated=2))
        self.assertEqual(request.call_args.kwargs["url"],
                         "https://api-seller.ozon.ru/v1/product/action/timer/update")

    def test_promo_does_not_accept_empty_json_from_http_error(self):
        from test_stocks_update_results import load_api
        from Stocks.services.update_result import UpdateResult
        http, _ = load_http([response({}, status=400)])
        api, _ = load_api("Stocks/api/ozon_api.py", [])
        api.send_request_with_retries = http.send_request_with_retries
        self.assertEqual(api.update_promo_timer([1, 2]), UpdateResult(failed=2))

    def test_retries_same_params_after_network_error(self):
        http, request = load_http([RequestFailure("timeout"), response({"status": "OK"})])
        params = {"limit": 20, "pageToken": "next"}
        self.assertEqual(http.send_request_with_retries("test", "POST", {}, params=params),
                         {"status": "OK"})
        self.assertEqual(request.call_count, 2)
        for call in request.call_args_list:
            self.assertEqual(call.kwargs["params"], params)
            self.assertEqual(call.kwargs["timeout"], (5, 30))

    def test_exhausted_retries_return_none(self):
        http, request = load_http([RequestFailure("timeout")] * 3)
        self.assertIsNone(http.send_request_with_retries("test", "POST", {}, params={"pageToken": "next"}))
        self.assertEqual(request.call_count, 3)

    def test_retries_server_errors_and_rate_limit(self):
        http, request = load_http([
            response({}, 500), response({}, 429, {"Retry-After": "1"}),
            response({"status": "OK"}),
        ])
        self.assertEqual(http.send_request_with_retries("test", "POST", {}, params={"limit": 20}),
                         {"status": "OK"})
        self.assertEqual(request.call_count, 3)

    def test_existing_positional_calls_still_work(self):
        http, request = load_http([response({"created": True}, 201)])
        self.assertEqual(http.send_request_with_retries("test", "POST", {}, {"a": 1}, 1, [201]),
                         {"created": True})
        self.assertIsNone(request.call_args.kwargs["params"])
        self.assertEqual(request.call_args.kwargs["json"], {"a": 1})

    def test_catalog_recovers_on_current_page_without_duplicates(self):
        from test_stocks_yandex_pagination import load_yandex_api, page
        http, request = load_http([
            response(page("A", "second")), RequestFailure("timeout"), response(page("B")),
        ])
        api = load_yandex_api(http.send_request_with_retries)
        self.assertEqual(api.get_sku_from_yandex(), [
            {"offer": {"offerId": "A"}}, {"offer": {"offerId": "B"}},
        ])
        self.assertEqual([call.kwargs["params"] for call in request.call_args_list], [
            {"limit": 20}, {"limit": 20, "pageToken": "second"},
            {"limit": 20, "pageToken": "second"},
        ])

    def test_catalog_failure_after_retries_never_returns_partial_list(self):
        from test_stocks_yandex_pagination import load_yandex_api, page
        from Stocks.services.catalog_errors import CatalogLoadError
        http, request = load_http([response(page("A", "second"))] + [RequestFailure("timeout")] * 3)
        api = load_yandex_api(http.send_request_with_retries)
        with self.assertRaises(CatalogLoadError) as raised:
            api.get_sku_from_yandex()
        self.assertEqual(raised.exception.loaded_count, 1)
        self.assertEqual(raised.exception.page_number, 2)
        self.assertEqual(request.call_count, 4)


if __name__ == "__main__":
    unittest.main()
