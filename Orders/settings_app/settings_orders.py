import os

from Common.settings import FTP_PATH, NAME_SHOP

ORDERS_DIR = os.path.join(FTP_PATH, "Orders", NAME_SHOP)
os.makedirs(ORDERS_DIR, exist_ok=True)

# Данные для записи в файл заказа .dbf
DIVISION_ID_IN_SUPPLIER_CRM = 19520
CUSTOMER_ID_IN_SUPPLIER_CRM = 994