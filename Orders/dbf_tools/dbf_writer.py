import dbf

from typing import List, Dict, Any, Optional
from Orders.utils.safe_cast import safe_str, safe_int, safe_float
from Orders.utils.validators import validate_product_record
from Orders.utils.date_utils import parse_iso_date
from Common.logger import get_logger
logger = get_logger("Orders")

DBF_STRUCT = (
    'offer_id C(50); name C(255); price N(10,2); qty N(10,0); '
    'post_num C(50); ord_date D; ship_date D; comment C(255); '
    'cust_id C(10); div_id C(10)'
)
DBF_CODEPAGE = 'cp866'


def save_to_dbf(
    filename: str,
    products: List[Dict[str, Any]],
    posting_number: str,
    order_date_iso: Optional[str],
    shipment_date_iso: Optional[str],
    comment_for_supplier: str,
    customer_id_in_supplier_crm: str,
    division_id: str
) -> None:

    if not products:
        logger.info(f"Posting {posting_number} не содержит products")
        return

    for p in products:
        ok, error_msg = validate_product_record(p)
        if not ok:
            logger.error(
                f"DBF НЕ создан для posting {posting_number}. "
                f"Ошибка в товаре {p}: {error_msg}"
            )
            return

    try:
        table = dbf.Table(filename, DBF_STRUCT, codepage=DBF_CODEPAGE)
        #table = Table(filename, DBF_STRUCT, codepage=DBF_CODEPAGE)
        table.open(mode=dbf.READ_WRITE)
    except Exception as e:
        logger.exception(f"Не удалось создать DBF {filename}: {e}")
        return

    try:
        for p in products:
            record = (
                safe_str(p.get('offer_id') or p.get('sku'), 50),
                safe_str(p.get('name'), 255),
                safe_float(p.get('price', {}).get('amount')),
                safe_int(p.get('quantity')),
                safe_str(posting_number, 50),
                parse_iso_date(order_date_iso),
                parse_iso_date(shipment_date_iso),
                safe_str(comment_for_supplier, 255),
                safe_str(customer_id_in_supplier_crm, 10),
                safe_str(division_id, 10),
            )
            table.append(record)

        logger.info(f"DBF сохранён: {posting_number}")

    finally:
        try:
            table.close()
        except Exception:
            logger.exception(f"Ошибка при закрытии DBF {filename}")
