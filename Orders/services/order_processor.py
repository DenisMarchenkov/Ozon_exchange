import os

from Orders.dbf_tools.dbf_writer import save_to_dbf
#from Common.settings import ORDER_DIR, CUSTOMER_ID_IN_SUPPLIER_CRM, DIVISION_ID_IN_SUPPLIER_CRM, SHOP_NAME
from Orders.settings_app.settings_orders import ORDERS_DIR, CUSTOMER_ID_IN_SUPPLIER_CRM, DIVISION_ID_IN_SUPPLIER_CRM, SHOP_NAME
from Common.logger import get_logger
from Orders.services.db_orders import get_order_status, create_order, update_order_status

logger = get_logger("Orders")


def save_to_files_server_response(resp):
    os.makedirs(ORDERS_DIR, exist_ok=True)

    if not resp or 'result' not in resp or 'postings' not in resp['result']:
        logger.error("Неправильный ответ от API: нет 'result.postings'")
        return

    for posting in resp['result']['postings']:
        posting_number = posting.get('posting_number')
        if not posting_number:
            logger.warning("В posting отсутствует posting_number, пропускаю.")
            continue

        status = get_order_status(posting_number)

        # Если уже создан DBF — пропускаем
        if status == "dbf_created":
            logger.info(f"{posting_number} уже обработан ранее")
            continue

        # Если отменён — пропускаем
        if status == "cancelled":
            logger.info(f"{posting_number} отменён — пропуск")
            continue

        # ЕСЛИ ЗАКАЗА НЕТ В БАЗЕ — СОЗДАЁМ СО СТАТУСОМ 'new'
        if status is None:
            logger.info(f"Новый заказ {posting_number}, создаю в БД со статусом 'new'")
            create_order(posting_number, "new")

        filename = os.path.join(ORDERS_DIR, f"{posting_number}.dbf")
        order_date_iso = posting.get('in_process_at')
        shipment_date_iso = posting.get('shipment_date')
        products = posting.get('products') or []
        comment_for_supplier = f'{posting_number} Заказ OZON {SHOP_NAME}'

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

            # ПОСЛЕ УСПЕШНОГО СОЗДАНИЯ DBF — ОБНОВЛЯЕМ СТАТУС
            update_order_status(posting_number, "dbf_created")
            logger.info(f"Статус заказа {posting_number} обновлён на dbf_created")

        except Exception as e:
            logger.exception(f"Ошибка при создании файла {filename}: {e}")