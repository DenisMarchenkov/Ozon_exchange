import pandas as pd

from Common.logger import get_logger
logger = get_logger("Stocks")

def prepare_offers_data(file_products) -> list[dict]:
    """
    Читает данные из основного файла XLS, выбирает количество товара и формирует список для обновления остатков.

    :param file_products: str - Путь к файлу (содержит колонки: 'Артикул', 'Количество').
    :return: list - Список словарей с обновленными данными.
    """
    try:
        # Загружаем основной файл
        logger.info("Загружаем данные из файла: %s", file_products)
        df_products = pd.read_excel(file_products)

        # Проверяем наличие нужных столбцов
        required_columns = {"Артикул", "Количество"}
        if not required_columns.issubset(df_products.columns):
            logger.error("Файл %s не содержит нужных столбцов.", file_products)
            raise ValueError(f"Файл {file_products} не содержит нужных столбцов")

        # Преобразование типов
        df_products['Артикул'] = df_products['Артикул'].astype(str)
        df_products['Количество'] = df_products['Количество'].fillna(0).astype(int)

        # Формируем список остатков
        logger.info("Формируем список остатков.")
        offers = []

        for _, row in df_products.iterrows():
            offer_id = row["Артикул"]
            count = row["Количество"]

            # logger.info("Товар: Артикул=%s, Количество=%d", offer_id, count)

            offers.append({
                "offerId": offer_id,
                "qua": count,
            })

        logger.info("Генерация списка остатков завершена.")
        return offers

    except Exception as e:
        logger.error("Произошла ошибка при обработке данных: %s", e)
        raise
