import os

from Common.settings import NAME_SHOP
from Orders.dbf_tools.dbf_writer import save_to_dbf
from Orders.settings_app.settings_orders import ORDERS_DIR, CUSTOMER_ID_IN_SUPPLIER_CRM, DIVISION_ID_IN_SUPPLIER_CRM
from Common.logger import get_logger
from Orders.db_orders.orders_repository import OrdersRepository

logger = get_logger("Orders")


def save_to_files_server_response(resp):
    os.makedirs(ORDERS_DIR, exist_ok=True)

    repo = OrdersRepository()

    if not resp or 'result' not in resp or 'postings' not in resp['result']:
        logger.error("Неправильный ответ от API: нет 'result.postings'")
        return

    for posting in resp['result']['postings']:
        posting_number = posting.get('posting_number')
        if not posting_number:
            logger.warning("В posting отсутствует posting_number, пропускаю.")
            continue

        status = repo.get_status(posting_number)

        if status == "dbf_created":
            logger.info(f"{posting_number} уже обработан ранее")
            continue

        if status == "cancelled":
            logger.info(f"{posting_number} отменён — пропуск")
            continue

        products = posting.get('products') or []
        requirements = posting.get('requirements') or {}
        non_empty_requirements = {
            key: value
            for key, value in requirements.items()
            if isinstance(value, list) and value
        }

        if status is None:
            logger.info(f"Новый заказ {posting_number}, создаю в БД со статусом 'new'")

            if not products:
                logger.warning(f"{posting_number}: нет products — заказ не сохранён в БД")
                continue

            items = [
                {
                    "product_id": p.get("sku", 'Unknow product'),
                    "offer_id": p.get("offer_id", 'Unknow product'),
                    "quantity": p.get("quantity", 'Unknow product'),
                }
                for p in products
            ]


            items = [i for i in items if i["quantity"] > 0 and i["offer_id"]]
            if not items:
                logger.warning(f"{posting_number}: все позиции пустые")
                continue

            has_requirements = bool(non_empty_requirements)

            repo.create_order_with_items(
                posting_number=posting_number,
                status="new",
                has_requirements=has_requirements,
                items=items
            )

            for req_type, values in non_empty_requirements.items():
                for value in values:
                    repo.create_requirements(posting_number, req_type, value)

        filename = os.path.join(ORDERS_DIR, f"{posting_number}.dbf")
        order_date_iso = posting.get('in_process_at')
        shipment_date_iso = posting.get('shipment_date')
        comment_for_supplier = f'{posting_number} Заказ OZON {NAME_SHOP}'

        if not products:
            logger.info(f"Posting {posting_number} не содержит products")
            continue

        try:
            save_to_dbf(
                filename=filename,
                products=products,
                posting_number=posting_number,
                order_date_iso=order_date_iso,
                shipment_date_iso=shipment_date_iso,
                comment_for_supplier=comment_for_supplier,
                customer_id_in_supplier_crm=str(CUSTOMER_ID_IN_SUPPLIER_CRM),
                division_id=str(DIVISION_ID_IN_SUPPLIER_CRM),
            )

            repo.update_status(posting_number, "dbf_created")
            logger.info(f"Статус заказа {posting_number} обновлён на dbf_created")

        except Exception as e:
            logger.exception(f"Ошибка при создании файла {filename}: {e}")
