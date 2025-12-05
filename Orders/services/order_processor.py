import os

from typing import Dict, Any
from Orders.dbf_tools.dbf_writer import save_to_dbf
from Common.settings import ORDER_DIR, CUSTOMER_ID_IN_SUPPLIER_CRM, DIVISION_ID_IN_SUPPLIER_CRM, SHOP_NAME
from Common.logger import get_logger
logger = get_logger("Orders")

def save_to_files_server_response(resp: Dict[str, Any]) -> None:
    os.makedirs(ORDER_DIR, exist_ok=True)
    if not resp or 'result' not in resp or 'postings' not in resp['result']:
        logger.error("Неправильный ответ от API: нет 'result.postings'")
        return

    for posting in resp['result']['postings']:
        posting_number = posting.get('posting_number')
        if not posting_number:
            logger.warning("В posting отсутствует posting_number, пропускаю.")
            continue

        filename = os.path.join(ORDER_DIR, f"{posting_number}.dbf")

        if os.path.exists(filename):
            logger.info(f'Файл {filename} уже существует — пропускаю posting {posting_number}')
            continue

        order_date_iso = posting.get('in_process_at')
        shipment_date_iso = posting.get('shipment_date')
        products = posting.get('products') or []

        comment_for_supplier = f'{posting_number} Заказ OZON {SHOP_NAME}'

        # Проверяем requirements — если есть непустые списки, логируем
        requirements = posting.get('requirements', {})
        non_empty_requirements = {k: v for k, v in requirements.items() if isinstance(v, list) and v}
        if non_empty_requirements:
            logger.info(f"Posting {posting_number} имеет обязательные требования: {non_empty_requirements}")

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
        except Exception as e:
            logger.exception(f"Ошибка при создании файла {filename} для posting {posting_number}: {e}")
