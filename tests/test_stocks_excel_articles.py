import io
import unittest
from datetime import datetime

import pandas as pd

from test_stocks_update_results import load_module, module_stub, load_app
import logging


def load_reader():
    return load_module("Stocks/readers/excel_reader.py", {
        "Common.logger": module_stub("Common.logger", get_logger=logging.getLogger),
    })


def xlsx(rows):
    buffer = io.BytesIO()
    pd.DataFrame(rows, columns=["Артикул", "Количество"]).to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer


class ExcelArticleTests(unittest.TestCase):
    def test_real_excel_preserves_leading_zeros_and_literal_na_articles(self):
        reader = load_reader()
        data = xlsx([("000829", 5), ("NA", 1), ("N/A", 2), ("nan", 3), ("NULL", 4)])
        offers = reader.prepare_offers_data(data)
        self.assertEqual({o["offerId"]: o["qua"] for o in offers}, {
            "000829": 5, "NA": 1, "N/A": 2, "nan": 3, "NULL": 4,
        })

    def test_numeric_articles_and_text_decimal_suffix_remain_distinct(self):
        reader = load_reader()
        offers = reader.prepare_offers_data(xlsx([(123, 5), ("123.0", 2), ("00123", 3)]))
        self.assertEqual({o["offerId"]: o["qua"] for o in offers}, {
            "123": 5, "123.0": 2, "00123": 3,
        })
        self.assertEqual(reader.normalize_article(123.0), "123")

    def test_trimmed_duplicates_are_grouped(self):
        reader = load_reader()
        offers = reader.prepare_offers_data(xlsx([("\u00a0A \t", 5), ("A", 2), ("B C", 1)]))
        self.assertEqual(offers, [{"offerId": "A", "qua": 7}, {"offerId": "B C", "qua": 1}])

    def test_blank_article_aborts_instead_of_returning_partial_price(self):
        reader = load_reader()
        with self.assertRaisesRegex(ValueError, "Excel 3"):
            reader.prepare_offers_data(xlsx([("A", 5), (None, 2)]))

    def test_ambiguous_article_types_are_rejected(self):
        reader = load_reader()
        for article in [True, 123.5, datetime(2026, 10, 14), float("nan"), "   "]:
            with self.subTest(article=article), self.assertRaises(ValueError):
                reader.normalize_article(article)

    def test_empty_quantity_still_means_zero(self):
        reader = load_reader()
        self.assertEqual(reader.prepare_offers_data(xlsx([("A", None)])), [{"offerId": "A", "qua": 0}])

    def test_invalid_article_prevents_marketplace_requests(self):
        reader = load_reader()
        app, _, ozon, yandex = load_app()
        app.prepare_offers_data = reader.prepare_offers_data
        with self.assertRaises(ValueError):
            app.start_exchange_stock(xlsx([("A", 5), (None, 2)]))
        ozon.get_sku_from_ozon.assert_not_called()
        yandex.get_sku_from_yandex.assert_not_called()
        ozon.update_stocks.assert_not_called()
        yandex.update_stocks_yandex.assert_not_called()

    def test_numeric_excel_article_matches_ozon_without_false_zero(self):
        reader = load_reader()
        app, _, ozon, _ = load_app()
        app.prepare_offers_data = reader.prepare_offers_data
        ozon.get_sku_from_ozon.return_value = [{"offer_id": "123", "product_id": 1}]
        actual = app.start_exchange_stock(xlsx([(123, 5)]))
        self.assertEqual(actual, [{"offer_id": "123", "product_id": 1, "stock": 5}])


class ExcelQuantityTests(unittest.TestCase):
    def test_integer_values_with_zero_fraction_are_accepted(self):
        reader = load_reader()
        offers = reader.prepare_offers_data(xlsx([
            ("A", "4,000"), ("B", 5.0), ("C", "6.000"), ("D", " 7,00 "),
        ]))
        self.assertEqual({o["offerId"]: o["qua"] for o in offers}, {"A": 4, "B": 5, "C": 6, "D": 7})

    def test_nonzero_fractions_are_rejected_without_rounding(self):
        reader = load_reader()
        for quantity in ["3,4", "5,84", 3.4, "-5,84", "4.0000000000000000001"]:
            with self.subTest(quantity=quantity), self.assertRaisesRegex(ValueError, "Excel 3.*артикул=B"):
                reader.prepare_offers_data(xlsx([("A", 1), ("B", quantity)]))

    def test_fractions_cannot_cancel_each_other_before_validation(self):
        reader = load_reader()
        with self.assertRaises(ValueError):
            reader.prepare_offers_data(xlsx([("A", "1,4"), ("A", "-0,4")]))

    def test_negative_corrections_are_summed_before_clamping(self):
        reader = load_reader()
        with self.assertLogs(reader.logger, level="WARNING") as logs:
            offers = reader.prepare_offers_data(xlsx([
                ("A", 10), ("A", -3), ("B", 3), ("B", -10), ("C", "-2,000"),
            ]))
        self.assertEqual(offers, [
            {"offerId": "A", "qua": 7}, {"offerId": "B", "qua": 0}, {"offerId": "C", "qua": 0},
        ])
        text = "\n".join(logs.output)
        self.assertNotIn("артикул=A", text)
        self.assertIn("артикул=B", text)
        self.assertIn("строки Excel=[4, 5]", text)
        self.assertIn("исходный итог=-7", text)

    def test_invalid_values_are_rejected(self):
        reader = load_reader()
        for quantity in ["нет", "nan", "inf", True, datetime(2026, 10, 14)]:
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                reader.normalize_quantity(quantity)

    def test_fraction_prevents_all_marketplace_requests(self):
        reader = load_reader()
        app, _, ozon, yandex = load_app()
        app.prepare_offers_data = reader.prepare_offers_data
        with self.assertRaises(ValueError):
            app.start_exchange_stock(xlsx([("A", "5,84")]))
        ozon.get_sku_from_ozon.assert_not_called()
        yandex.get_sku_from_yandex.assert_not_called()
        ozon.update_stocks.assert_not_called()
        yandex.update_stocks_yandex.assert_not_called()


if __name__ == "__main__":
    unittest.main()
