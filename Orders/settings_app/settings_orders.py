import os

from Common.settings import SUPPLIER_SOURCE



ORDERS_DIR = os.path.join(SUPPLIER_SOURCE, "Orders")
os.makedirs(ORDERS_DIR, exist_ok=True)


# Данные для записи в файл заказа .dbf
SHOP_NAME = "Best seller ever"
DIVISION_ID_IN_SUPPLIER_CRM = 10001
CUSTOMER_ID_IN_SUPPLIER_CRM = 101