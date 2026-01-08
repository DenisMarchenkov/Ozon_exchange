import math
import pandas as pd

from typing import Dict
from Common.time import now_iso
from Prices.settings_app.settings_prices import MISSING_DATA_MARKUP, MISSING_COEFFICIENT_OLD_PRICE, MISSING_COEFFICIENT_MIN_PRICE
from Common.logger import get_logger
logger = get_logger(__name__)

class MarkupReader:
    """
    Класс для чтения глобальной и ручной наценки из Excel файла.

    Атрибуты:
        path (str): путь к Excel-файлу с наценками.
        df_global (DataFrame): таблица глобальной наценки.
        df_manual (DataFrame): таблица ручной наценки.
    """

    def __init__(self, path: str):
        self.path = path
        self.df_global = None
        self.df_manual = None

        logger.info(f"Загрузка файла наценок: {path}")
        self._load_excel()

    def _load_excel(self):
        """Считывает Excel один раз при создании класса."""
        try:
            self.df_global = pd.read_excel(
                self.path, header=[0, 1], sheet_name="Global_markup"
            )
            self.df_manual = pd.read_excel(
                self.path, sheet_name="Manual_markup"
            )
            logger.info("Наценки успешно загружены.")
        except Exception as e:
            logger.error(f"Ошибка при чтении Excel: {e}")
            raise


    def get_global_markup(self) -> Dict:
        """Возвращает структуру глобальной наценки из последней строки таблицы."""
        df = self.df_global

        if df.empty:
            logger.error("Лист Global_markup пуст.")
            raise ValueError("Лист Global_markup пуст или повреждён")

        last_row = df.iloc[-1]
        multi_cols_data = last_row.iloc[2:]  # Пропускаем первые 2 служебные столбца

        result = {}
        for (top, sub), value in multi_cols_data.items():
            result.setdefault(top, {})[sub] = float(value)

        logger.debug(f"Глобальная наценка: {result}")
        return result


    def get_manual_markup(self) -> Dict[str, Dict[str, float]]:
        """Возвращает словарь ручных наценок по SKU."""
        df = self.df_manual

        if df.empty:
            logger.warning("В листе Manual_markup нет данных.")
            return {}

        # Фильтруем строки без даты отключения и без NaN в ключевых столбцах
        df_filtered = (
            df[df["Дата отключения"].isna()]
            .dropna(subset=["Артикул", "наценка"])
            [["Артикул", "наценка"]]
        )

        result = {
            str(row["Артикул"]).strip(): {"manual_markup_value": float(row["наценка"])}
            for row in df_filtered.to_dict("records")
        }

        logger.debug(f"Ручные наценки: {result}")
        return result

    def load_all(self) -> Dict[str, object]:
        """Возвращает глобальную и ручную наценку одним словарём."""
        return {
            "global": self.get_global_markup(),
            "manual": self.get_manual_markup(),
        }


# =================================================================

class ProductReader:
    """
    Класс для чтения списка товаров (SKU, бренд, цена поставщика) из Excel.

    Атрибуты:
        path (str): путь к файлу товаров.
        df (DataFrame): загруженный список товаров.
    """

    def __init__(self, path: str):
        self.path = path
        self.df = None

        logger.info(f"Загрузка списка товаров: {path}")
        self._load_excel()

    def _load_excel(self):
        """Читает Excel с товарами и проверяет обязательные колонки."""
        try:
            self.df = pd.read_excel(self.path)

            expected_cols = ["Артикул", "Mark", "Price"]
            for col in expected_cols:
                if col not in self.df.columns:
                    raise ValueError(f"В файле {self.path} отсутствует колонка: {col}")

            logger.info("Список товаров успешно загружен.")
        except Exception as e:
            logger.error(f"Ошибка чтения файла товаров: {e}")
            raise

    def get_products(self) -> dict[str, dict]:
        """Возвращает словарь товаров: {SKU: {"brand": ..., "supplier_price": ...}}."""

        result = {}
        for row in self.df.to_dict("records"):
            sku = str(row["Артикул"]).strip()
            result[sku] = {
                "brand": str(row["Mark"]).strip(),
                "supplier_price": float(row["Price"])
            }

        logger.debug(f"Загружено товаров: {len(result)}")
        return result


# =================================================================

class PricingEngine:
    """
    Класс для расчёта всех типов цен для Ozon:
        - price
        - min_price
        - old_price
        - признак ручной наценки
    """

    def __init__(self, global_data: dict, manual_data: dict, price_repo, supplier_price_id: str):
        self.global_data = global_data or {}
        self.manual_map = manual_data or {}
        self.price_repo = price_repo
        self.supplier_price_id = supplier_price_id

        logger.info("Инициализация ценового движка.")

        # Индекс брендов для быстрого поиска
        self.brand_index = {
            self._norm_brand(k): v
            for k, v in (global_data or {}).items()
            if k != "old_price"
        }

    @staticmethod
    def _norm_sku(sku: str) -> str:
        return sku.strip()

    @staticmethod
    def _norm_brand(brand: str) -> str:
        if not brand:
            return ""
        return str(brand).strip()

    def get_manual_markup(self, sku: str) -> float | None:
        sku_norm = self._norm_sku(sku)
        if sku_norm in self.manual_map:
            logger.debug(f"Найдена ручная наценка для {sku_norm}")
            return float(self.manual_map[sku_norm]["manual_markup_value"])
        return None

    def get_brand_markup(self, brand: str) -> dict | None:
        return self.brand_index.get(self._norm_brand(brand))

    @staticmethod
    def calc_price(base: float, coefficient: float) -> float:
        return base * coefficient


    def safe_number(self, value):
        """Возвращает число, если оно валидное, иначе None."""
        if isinstance(value, (int, float)) and not math.isnan(value):
            return value
        return None


    def calculate_price(self, sku: str, brand: str, supplier_price: float) -> dict[str, float | bool] | None:
        """Основной расчёт цен."""
        logger.debug(f"Расчёт цены для SKU={sku}")

        # --- Читаем данные ---
        manual_markup = self.safe_number(self.get_manual_markup(sku))
        brand_markup = self.get_brand_markup(brand) or {}

        brand_price = self.safe_number(brand_markup.get("price"))
        brand_min_price = self.safe_number(brand_markup.get("min_price"))
        brand_old_price = self.safe_number(brand_markup.get("old_price"))

        # --- Фолбэки ---
        fallback_price = supplier_price * MISSING_DATA_MARKUP
        fallback_min_price = supplier_price * (MISSING_DATA_MARKUP - MISSING_COEFFICIENT_MIN_PRICE)
        fallback_old_price = supplier_price * (MISSING_DATA_MARKUP + MISSING_COEFFICIENT_OLD_PRICE)

        # ======================================================
        # === 1. Есть ручная наценка — используем её приоритет
        # ======================================================
        if manual_markup is not None:
            logger.info(f"Используется ручная наценка {manual_markup} для {sku}")

            price = self.calc_price(supplier_price, manual_markup)

            # ---- min_price ----
            if brand_min_price is not None:
                min_price = self.calc_price(supplier_price, brand_min_price)
            else:
                logger.warning(
                    f"[SKU={sku}] Нет brand_min_price → используется ручная наценка - MISSING_COEFFICIENT_MIN_PRICE"
                )
                min_price = self.calc_price(
                    supplier_price,
                    manual_markup - MISSING_COEFFICIENT_MIN_PRICE
                )

            # ---- old_price ----
            if manual_markup is not None:
                old_price = self.calc_price(
                    supplier_price,
                    manual_markup + MISSING_COEFFICIENT_OLD_PRICE
                )
            else:
                logger.warning(
                    f"[SKU={sku}] Нет manual_markup для old_price → fallback_old_price"
                )
                old_price = fallback_old_price

            return {
                "price": price,
                "min_price": min_price,
                "old_price": old_price,
                "manual": True
            }

        # ======================================================
        # === 2. Нет ручной — используем наценку бренда
        # ======================================================
        if brand_markup:
            logger.info(f"Используется глобальная наценка бренда '{brand}' для SKU={sku}")

            # ---- price ----
            if brand_price is not None:
                price = self.calc_price(supplier_price, brand_price)
            else:
                logger.warning(f"[SKU={sku}] Нет brand_price → fallback_price")
                price = fallback_price

            # ---- min_price ----
            if brand_min_price is not None:
                min_price = self.calc_price(supplier_price, brand_min_price)
            else:
                logger.warning(
                    f"[SKU={sku}] Нет brand_min_price → brand_price - MISSING_COEFFICIENT_MIN_PRICE"
                )
                min_price = self.calc_price(
                    supplier_price,
                    brand_price - MISSING_COEFFICIENT_MIN_PRICE
                )

            # ---- old_price ----
            if brand_old_price is not None:
                old_price = self.calc_price(supplier_price, brand_old_price)
            else:
                logger.warning(
                    f"[SKU={sku}] Нет brand_old_price → brand_price + MISSING_COEFFICIENT_OLD_PRICE"
                )
                old_price = self.calc_price(
                    supplier_price,
                    brand_price + MISSING_COEFFICIENT_OLD_PRICE
                )

            return {
                "price": price,
                "min_price": min_price,
                "old_price": old_price,
                "manual": False
            }

        # ======================================================
        # === 3. Нет данных нигде — полный fallback ===
        # ======================================================
        logger.warning(f"Нет данных наценки для SKU={sku}, используется полный fallback")

        # return {
        #     "price": fallback_price,
        #     "min_price": fallback_min_price,
        #     "old_price": fallback_old_price,
        #     "manual": False
        # }
        return None


    def build_ozon_record(self, sku: str, supplier_price: float, calc: dict) -> dict:
        """Создаёт структуру записи для API Ozon."""
        final_calc = self.finalize_calc(calc)
        logger.debug(
            f"SKU={sku} | поставщик={supplier_price} | min={round(calc['min_price'])} | "
            f"price={round(calc['price'])} | old={round(calc['old_price'])} | manual={calc['manual']}"
        )

        self.price_repo.save_price_calculation(
            supplier_price_id=self.supplier_price_id,
            sku_art=sku,
            supplier_price=supplier_price,
            calc=final_calc,
            created_at=now_iso()
        )

        return {
            "auto_action_enabled": "UNKNOWN",
            "auto_add_to_ozon_actions_list_enabled": "UNKNOWN",
            "currency_code": "RUB",
            "manage_elastic_boosting_through_price": False,
            "min_price": str(final_calc["min_price"]),
            "min_price_for_auto_actions_enabled": True,
            "offer_id": sku,
            "old_price": str(final_calc["old_price"]),
            "price": str(final_calc["price"]),
            "price_strategy_enabled": "UNKNOWN",
        }

    def process_product(self, product: dict) -> dict | None:
        """Обрабатывает один товар — считает все цены и возвращает JSON для Ozon."""
        sku = product["sku"]
        brand = product.get("brand")
        supplier_price = float(product["supplier_price"])

        calc = self.calculate_price(sku, brand, supplier_price)
        # Если нет расчёта — пропуск
        if calc is None:
            return None

        return self.build_ozon_record(sku, supplier_price, calc)


    def run(self, products: dict) -> list:
        """Обрабатывает весь список товаров."""
        logger.info("Формирование цен по всем товарам...")

        result = []
        for k, v in products.items():
            try:
                item = self.process_product({"sku": k, **v})

                # Если calculate_price вернул None → пропускаем
                if item is None:
                    logger.warning(f"Товар {k} пропущен из-за отсутствующей наценки.")
                    continue

                result.append(item)

            except Exception as e:
                logger.error(f"Ошибка при обработке товара {k}: {e}")
                continue

        logger.info(f"Цены сформированы: {len(result)} позиций.")
        return result

    @staticmethod
    def finalize_calc(calc: dict[str, float | bool]) -> dict[str, int | bool]:
        """
        Округляет все цены по правилам для Ozon и БД.
        Возвращает финальный словарь с int значениями для price, min_price, old_price.
        """
        def round_price(value: float) -> int:
            # пример твоего правила: округляем до целого,
            # если заканчивается на 5, то округляем вниз
            rounded = int(value + 0.5)
            if (value * 10) % 10 == 5:  # если десятая равна 5
                rounded = int(value)
            return rounded

        return {
            "price": round_price(calc["price"]),
            "min_price": round_price(calc["min_price"]),
            "old_price": round_price(calc["old_price"]),
            "manual": calc["manual"],
        }


# =================================================================

def prepare_batches(items, batch_size=300):
    """
    Разбивает список items на партии.
    """
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i:i + batch_size])

    logger.info(f"Разбито на {len(batches)} партий.")
    return batches