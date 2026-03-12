from Common.settings import WAREHOUSE_ID

def prepare_batches(offers, batch_size=90):
    """
    Разбивает список товаров на партии и формирует JSON-структуру.

    :param offers: list - Список товаров [{"offerId": str, "qua": int}, ...]
    :param batch_size: int - Максимальное количество товаров в одном запросе.
    :return: list - Список JSON-объектов для API.
    """
    batches = []
    for i in range(0, len(offers), batch_size):
        batch = offers[i:i + batch_size]
        batch_json = {
            "stocks": [
                {
                    "offer_id": offer["offer_id"],  # Значение артикулов
                    "stock": offer["stock"],
                    "warehouse_id": WAREHOUSE_ID
                }
                for offer in batch  # Генерация списка "skus"
            ]
        }
        batches.append(batch_json)

    return batches

def chunk_list(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def prepare_batches_yandex(offers, batch_size=150):
    """
    Разбивает список товаров на партии и формирует JSON-структуру для Yandex API.

    :param offers: list - Список товаров [{"sku": str, "items": [{"count": int}]}]
    :param batch_size: int - Максимальное количество товаров в одном запросе.
    :return: list - Список JSON-объектов с ключом "skus".
    """
    batches = []
    for i in range(0, len(offers), batch_size):
        batch = {"skus": offers[i:i + batch_size]}
        batches.append(batch)
    return batches