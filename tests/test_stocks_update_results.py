import importlib.util
import logging
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

from Stocks.services.update_result import UpdateResult
from Stocks.services.catalog_errors import CatalogLoadError


ROOT = Path(__file__).resolve().parents[1]


def module_stub(name, **attributes):
    module = ModuleType(name)
    module.__dict__.update(attributes)
    return module


def load_module(path, dependencies):
    spec = importlib.util.spec_from_file_location("stocks_under_test", ROOT / path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict("sys.modules", dependencies):
        spec.loader.exec_module(module)
    return module


def load_api(path, responses):
    send = Mock(side_effect=responses)
    settings = module_stub("Common.settings", **dict.fromkeys([
        "WAREHOUSE_ID", "API_TOKEN", "CLIENT_ID", "YANDEX_API_TOKEN",
        "YANDEX_BUSINESS_ID", "YANDEX_CAMPAIGN_ID",
    ], "test"))
    dependencies = {
        "Common.settings": settings,
        "Common.logger": module_stub("Common.logger", get_logger=logging.getLogger),
        "Common.http_utils": module_stub("Common.http_utils", send_request_with_retries=send),
        "requests": module_stub("requests", post=Mock(side_effect=AssertionError("Network forbidden"))),
        "time": module_stub("time", sleep=Mock()),
    }
    processor = load_module("Stocks/services/stock_processor.py", dependencies)
    dependencies["Stocks.services.stock_processor"] = processor
    return load_module(path, dependencies), send


def ozon_item(offer_id, updated=True, errors=None, warehouse="test"):
    return {"offer_id": offer_id, "warehouse_id": warehouse,
            "updated": updated, "errors": errors or []}


class StockApiResultTests(unittest.TestCase):
    def test_yandex_uses_versioned_stock_endpoint_and_preserves_payload(self):
        api, send = load_api("Stocks/api/yandex_api.py", [{"status": "OK"}])
        offers = [{"sku": "A", "items": [{"count": 5}]}]
        result = api.update_stocks_yandex(offers)
        send.assert_called_once_with(
            url="https://api.partner.market.yandex.ru/v2/campaigns/test/offers/stocks",
            method="PUT",
            headers={"Api-Key": "test", "Accept": "application/json",
                     "X-Market-Integration": "OrderGuard_V2"},
            body={"skus": offers},
        )
        self.assertEqual(result, UpdateResult(updated=1))

    def test_ozon_full_confirmation_is_successful(self):
        api, _ = load_api("Stocks/api/ozon_api.py", [{"result": [ozon_item("A")]}])
        result = api.update_stocks([{"offer_id": "A", "stock": 5}])
        self.assertEqual(result, UpdateResult(updated=1))
        self.assertEqual(result.status, "SUCCESS")

    def test_ozon_counts_individual_confirmations(self):
        api, _ = load_api("Stocks/api/ozon_api.py", [{"result": [
            ozon_item("A"), ozon_item("A"),
            ozon_item("B", errors=[{"code": "rejected"}]),
            ozon_item("C", warehouse="another-warehouse"),
            ozon_item("unrequested"),
        ]}])
        offers = [{"offer_id": key, "stock": 5} for key in "ABCD"]
        result = api.update_stocks(offers)
        self.assertEqual(result, UpdateResult(updated=1, failed=3))
        self.assertEqual(result.status, "PARTIAL")

    def test_ozon_continues_after_failed_batch(self):
        api, send = load_api("Stocks/api/ozon_api.py", [
            RuntimeError("request failed"), {"result": [ozon_item("90")]},
        ])
        result = api.update_stocks([{"offer_id": str(i), "stock": 5} for i in range(91)])
        self.assertEqual(result, UpdateResult(updated=1, failed=90))
        self.assertEqual(send.call_count, 2)

    def test_ozon_rejects_missing_or_malformed_confirmation(self):
        for response in [None, {}, {"result": True}, {"result": []},
                         {"result": [ozon_item("A", updated=False)]}]:
            with self.subTest(response=response):
                api, _ = load_api("Stocks/api/ozon_api.py", [response])
                result = api.update_stocks([{"offer_id": "A", "stock": 5}])
                self.assertEqual(result, UpdateResult(failed=1))
                self.assertEqual(result.status, "ERROR")

    def test_yandex_partial_update_preserves_successful_count(self):
        api, send = load_api("Stocks/api/yandex_api.py", [{"status": "OK"}, None])
        result = api.update_stocks_yandex([
            {"sku": str(i), "items": [{"count": 5}]} for i in range(151)
        ])
        self.assertEqual(result, UpdateResult(updated=150, failed=1))
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(send.call_count, 2)

    def test_yandex_rejects_errors_and_unexpected_responses(self):
        for response in [None, {}, {"status": "ERROR"},
                         {"status": "OK", "errors": [{"code": "invalid"}]},
                         RuntimeError("request failed")]:
            with self.subTest(response=response):
                api, _ = load_api("Stocks/api/yandex_api.py", [response])
                result = api.update_stocks_yandex([{"sku": "A", "items": [{"count": 5}]}])
                self.assertEqual(result, UpdateResult(failed=1))

    def test_empty_updates_make_no_requests(self):
        for path, name in [
            ("Stocks/api/ozon_api.py", "update_stocks"),
            ("Stocks/api/yandex_api.py", "update_stocks_yandex"),
            ("Stocks/api/ozon_api.py", "update_promo_timer"),
        ]:
            with self.subTest(name=name):
                api, send = load_api(path, [])
                self.assertEqual(getattr(api, name)([]).status, "SKIPPED")
                send.assert_not_called()

    def test_promo_partial_update_and_failed_responses(self):
        for failure in [None, {"result": True}, {"result": False}, {"errors": ["rejected"]},
                        {"result": "test_ok"}, {"unexpected": True}, RuntimeError("request failed")]:
            with self.subTest(failure=failure):
                api, _ = load_api("Stocks/api/ozon_api.py", [{}, failure])
                result = api.update_promo_timer([1, 2, 3], batch_size=2)
                self.assertEqual(result, UpdateResult(updated=2, failed=1))

    def test_promo_full_confirmation_is_successful(self):
        api, _ = load_api("Stocks/api/ozon_api.py", [{}])
        result = api.update_promo_timer([1, 2])
        self.assertEqual(result, UpdateResult(updated=2))
        self.assertEqual(result.status, "SUCCESS")


def load_app(dry_run=False):
    repo = Mock()
    repo.create_stock_update_session.side_effect = [1, 2]
    repo.create_promo_timer_session.return_value = 3
    ozon = module_stub("Stocks.api.ozon_api",
        get_sku_from_ozon=Mock(return_value=[{"offer_id": "A", "product_id": 1}]),
        update_stocks=Mock(return_value=UpdateResult(failed=1)),
        update_promo_timer=Mock(return_value=UpdateResult(failed=1)),
        get_marked_products=Mock())
    yandex = module_stub("Stocks.api.yandex_api",
        get_sku_from_yandex=Mock(return_value=[{"offer": {"offerId": "A"}}]),
        update_stocks_yandex=Mock(return_value=UpdateResult(failed=1)))
    dependencies = {
        "Stocks.api.ozon_api": ozon,
        "Stocks.api.yandex_api": yandex,
        "Stocks.readers.excel_reader": module_stub("Stocks.readers.excel_reader",
            prepare_offers_data=Mock(return_value=[{"offerId": "A", "qua": 5}])),
        "Stocks.db_stocks.stocks_repository": module_stub("Stocks.db_stocks.stocks_repository",
            StocksRepository=Mock(return_value=repo)),
        "Common.file_utils": module_stub("Common.file_utils", copy_file_with_timestamp=Mock()),
        "Common.settings": module_stub("Common.settings", SUPPLIER_SOURCE_FILE="test", SUPPLIER_PRICE_FOLDER="test"),
        "Common.logger": module_stub("Common.logger", get_logger=logging.getLogger),
        "Stocks.settings_app.settings_stocks": module_stub("Stocks.settings_app.settings_stocks",
            ENABLE_OZON=True, ENABLE_YANDEX=True, ENABLE_PROMO_TIMER=True, DRY_RUN=dry_run),
    }
    return load_module("Stocks/app_stocks.py", dependencies), repo, ozon, yandex


class StockSessionResultTests(unittest.TestCase):
    def test_failed_ozon_catalog_does_not_block_yandex_or_start_promo(self):
        app, repo, ozon, yandex = load_app()
        ozon.get_sku_from_ozon.side_effect = CatalogLoadError(2, 20, "timeout")
        yandex.update_stocks_yandex.return_value = UpdateResult(updated=1)
        app.main()
        ozon.update_stocks.assert_not_called()
        ozon.update_promo_timer.assert_not_called()
        repo.create_promo_timer_session.assert_not_called()
        repo.save_stock_history_bulk.assert_not_called()
        yandex.update_stocks_yandex.assert_called_once()
        self.assertEqual([c.args for c in repo.finish_stock_update_session.call_args_list], [
            (1, 0, "ERROR: CATALOG_LOAD_FAILED"), (2, 1, "SUCCESS"),
        ])
        self.assertIsNone(repo.create_stock_update_session.call_args_list[0].kwargs["total_ozon"])

    def test_both_catalog_failures_are_logged_without_sending(self):
        app, repo, ozon, yandex = load_app()
        ozon.get_sku_from_ozon.side_effect = CatalogLoadError(1, 0, "timeout")
        yandex.get_sku_from_yandex.side_effect = CatalogLoadError(2, 20, "timeout")
        with self.assertLogs(app.logger, level="WARNING") as logs:
            self.assertEqual(app.start_exchange_stock("test"), [])
        ozon.update_stocks.assert_not_called()
        yandex.update_stocks_yandex.assert_not_called()
        self.assertEqual([c.args for c in repo.finish_stock_update_session.call_args_list], [
            (1, 0, "ERROR: CATALOG_LOAD_FAILED"), (2, 0, "ERROR: CATALOG_LOAD_FAILED"),
        ])
        self.assertIn("Ozon=ERROR: CATALOG_LOAD_FAILED, Яндекс=ERROR: CATALOG_LOAD_FAILED",
                      "\n".join(logs.output))

    def test_failed_yandex_catalog_skips_sending_and_keeps_ozon_working(self):
        for dry_run in [False, True]:
            with self.subTest(dry_run=dry_run):
                app, repo, ozon, yandex = load_app(dry_run=dry_run)
                yandex.get_sku_from_yandex.side_effect = CatalogLoadError(2, 20, "timeout")
                ozon.update_stocks.return_value = UpdateResult(updated=1)
                app.start_exchange_stock("test")
                yandex.update_stocks_yandex.assert_not_called()
                repo.save_yandex_stock_history_bulk.assert_not_called()
                if not dry_run:
                    ozon.update_stocks.assert_called_once()
                self.assertEqual(repo.finish_stock_update_session.call_args_list[-1].args,
                                 (2, 0, "ERROR: CATALOG_LOAD_FAILED"))
                self.assertIsNone(repo.create_stock_update_session.call_args.kwargs["total_ozon"])

    def test_api_failures_are_not_logged_as_success(self):
        app, repo, _, _ = load_app()
        app.start_exchange_stock("test")
        self.assertEqual([c.args for c in repo.finish_stock_update_session.call_args_list], [
            (1, 0, "ERROR"), (2, 0, "ERROR"),
        ])
        app.start_update_promo_timer([{"product_id": 1}])
        repo.finish_promo_timer_session.assert_called_once_with(3, "ERROR")

    def test_partial_and_successful_results_reach_database(self):
        app, repo, ozon, yandex = load_app()
        ozon.update_stocks.return_value = UpdateResult(updated=1, failed=1)
        yandex.update_stocks_yandex.return_value = UpdateResult(updated=1)
        app.start_exchange_stock("test")
        self.assertEqual([c.args for c in repo.finish_stock_update_session.call_args_list], [
            (1, 1, "PARTIAL"), (2, 1, "SUCCESS"),
        ])
        ozon.update_promo_timer.return_value = UpdateResult(updated=1, failed=1)
        app.start_update_promo_timer([{"product_id": 1}, {"product_id": 2}])
        repo.finish_promo_timer_session.assert_called_once_with(3, "PARTIAL")

    def test_dry_run_makes_no_update_requests(self):
        app, repo, ozon, yandex = load_app(dry_run=True)
        app.start_exchange_stock("test")
        app.start_update_promo_timer([{"product_id": 1}])
        ozon.update_stocks.assert_not_called()
        yandex.update_stocks_yandex.assert_not_called()
        ozon.update_promo_timer.assert_not_called()
        self.assertEqual([c.args for c in repo.finish_stock_update_session.call_args_list], [
            (1, 0, "DRY_RUN"), (2, 0, "DRY_RUN"),
        ])
        repo.finish_promo_timer_session.assert_called_once_with(3, "DRY_RUN")


class StockLoggingTests(unittest.TestCase):
    def test_numeric_warehouse_matches_string_setting_without_false_errors(self):
        api, _ = load_api("Stocks/api/ozon_api.py", [{"result": [
            ozon_item("A", warehouse=1020001059810000),
            ozon_item("B", updated=False, warehouse=1020001059810000,
                      errors=[{"code": "rejected"}]),
            ozon_item("C", warehouse=999),
        ]}])
        batch = {"stocks": [
            {"offer_id": key, "warehouse_id": "1020001059810000", "stock": 5}
            for key in "ABC"
        ]}
        api.prepare_batches = Mock(return_value=[batch])
        with self.assertLogs(api.logger, level="INFO") as logs:
            result = api.update_stocks([{"offer_id": key, "stock": 5} for key in "ABC"])
        self.assertEqual(result, UpdateResult(updated=1, failed=2))
        text = "\n".join(logs.output)
        self.assertNotIn("offer_id=A", text)
        self.assertIn("offer_id=B", text)
        self.assertIn("rejected", text)
        self.assertIn("offer_id=C", text)

    def test_ozon_logs_rejected_and_missing_products(self):
        api, _ = load_api("Stocks/api/ozon_api.py", [{"result": [
            ozon_item("A"),
            ozon_item("B", updated=False, errors=[{
                "code": "offer_id_not_found", "message": "Product not found",
            }]),
        ]}])
        with self.assertLogs(api.logger, level="INFO") as logs:
            api.update_stocks([{"offer_id": key, "stock": 5} for key in "ABC"])
        text = "\n".join(logs.output)
        self.assertIn("offer_id=B", text)
        self.assertIn("offer_id_not_found", text)
        self.assertIn("Product not found", text)
        self.assertIn("offer_id=C", text)
        self.assertIn("warehouse_id=test", text)
        self.assertIn("status=PARTIAL", text)
        self.assertIn("WARNING", text)

    def test_yandex_logs_api_error_and_failed_skus_without_headers(self):
        api, _ = load_api("Stocks/api/yandex_api.py", [{
            "status": "ERROR", "errors": [{"code": "INVALID_SKU", "message": "Invalid SKU"}],
            "headers": {"Api-Key": "secret-must-not-be-logged"},
        }])
        with self.assertLogs(api.logger, level="ERROR") as logs:
            api.update_stocks_yandex([{"sku": "bad-sku", "items": [{"count": 5}]}])
        text = "\n".join(logs.output)
        self.assertIn("INVALID_SKU", text)
        self.assertIn("bad-sku", text)
        self.assertIn("status=ERROR", text)
        self.assertNotIn("secret-must-not-be-logged", text)

    def test_promo_logs_missing_response_and_product_ids(self):
        api, _ = load_api("Stocks/api/ozon_api.py", [None])
        with self.assertLogs(api.logger, level="ERROR") as logs:
            api.update_promo_timer([123])
        text = "\n".join(logs.output)
        self.assertIn("product_ids=[123]", text)
        self.assertIn("ответ API не получен", text)
        self.assertIn("status=ERROR", text)

    def test_dry_run_logs_session_and_disabled_sending(self):
        app, _, _, _ = load_app(dry_run=True)
        with self.assertLogs(app.logger, level="INFO") as logs:
            app.start_exchange_stock("test")
        text = "\n".join(logs.output)
        self.assertIn("status=DRY_RUN, session_id=1", text)
        self.assertIn("status=DRY_RUN, session_id=2", text)
        self.assertIn("отправка отключена", text)


if __name__ == "__main__":
    unittest.main()
