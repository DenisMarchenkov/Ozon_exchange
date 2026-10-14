import pandas as pd
from numbers import Integral, Real
import math

from Common.logger import get_logger
logger = get_logger("Stocks")


def normalize_article(value) -> str:
    """Сохраняет текстовый SKU и убирает .0 только у числовой ячейки."""
    if isinstance(value, str):
        article = value.strip()
        if not article:
            raise ValueError("пустой артикул")
        return article
    if pd.isna(value):
        raise ValueError("пустой артикул")
    if isinstance(value, bool):
        raise ValueError("артикул содержит логическое значение вместо текста или числа")
    if isinstance(value, Integral):
        return str(int(value))
    if isinstance(value, Real) and math.isfinite(value) and float(value).is_integer():
        return str(int(value))
    raise ValueError("артикул должен быть текстом или целым числом; проверьте формат ячейки")


def prepare_offers_data(file_products) -> list[dict]:
    """
    Читает данные из основного файла XLS, выбирает количество товара и формирует список для обновления остатков.

    :param file_products: str - Путь к файлу (содержит колонки: 'Артикул', 'Количество').
    :return: list - Список словарей с обновленными данными.
    """
    try:
        # Загружаем основной файл
        logger.info("Загружаем данные из файла: %s", file_products)
        # Не определяем числовой тип для всего столбца: это теряет ведущие нули.
        # NA, N/A, NULL и nan могут быть буквальными артикулами.
        df_products = pd.read_excel(
            file_products, dtype={"Артикул": object}, keep_default_na=False,
            na_values={"Количество": [""]},
        )

        # Проверяем наличие нужных столбцов
        required_columns = {"Артикул", "Количество"}
        if not required_columns.issubset(df_products.columns):
            logger.error("Файл %s не содержит нужных столбцов.", file_products)
            raise ValueError(f"Файл {file_products} не содержит нужных столбцов")

        # Преобразование типов
        articles = []
        normalized_count = 0
        for excel_row, value in enumerate(df_products["Артикул"], start=2):
            try:
                article = normalize_article(value)
            except ValueError as e:
                raise ValueError(f"Некорректный артикул в строке Excel {excel_row}: {e}") from e
            articles.append(article)
            if not isinstance(value, str) or article != value:
                normalized_count += 1
        df_products["Артикул"] = articles
        logger.info("Проверка артикулов завершена: строк=%s, нормализовано=%s",
                    len(articles), normalized_count)
        df_products['Количество'] = df_products['Количество'].fillna(0).astype(int)

        # Формируем список остатков (группируем по Артикулу для суммирования количества)
        logger.info("Формируем список остатков.")
        
        # Группируем и суммируем
        df_grouped = df_products.groupby('Артикул', as_index=False)['Количество'].sum()
        
        offers = []
        for _, row in df_grouped.iterrows():
            offer_id = str(row["Артикул"])
            count = int(row["Количество"])

            offers.append({
                "offerId": offer_id,
                "qua": count,
            })

        logger.info("Генерация списка остатков завершена. Уникальных товаров: %d", len(offers))
        return offers

    except Exception as e:
        logger.error("Произошла ошибка при обработке данных: %s", e)
        raise
