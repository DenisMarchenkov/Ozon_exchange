import os

from Common.settings import BASE_DIR, ARCHIVE_DIR, NAME_SHOP, FTP_PATH

CONFIRMATIONS_DIR = os.path.join(FTP_PATH, "Confirmations", NAME_SHOP)
os.makedirs(CONFIRMATIONS_DIR, exist_ok=True)

# папка с приложением
APP_DIR = os.path.join(BASE_DIR, "Confirmations")

# папка с настройками для приложения
SETTINGS_APP_DIR = os.path.join(APP_DIR, "settings_app")

# папка для архивных файлов
ARCHIVE_DIR_CONFIRMATIONS = os.path.join(ARCHIVE_DIR, "Confirmations")
os.makedirs(ARCHIVE_DIR_CONFIRMATIONS, exist_ok=True)

# папка для архивных файлов наклеек
ARCHIVE_DIR_LABELS = os.path.join(ARCHIVE_DIR, "Labels")
os.makedirs(ARCHIVE_DIR_LABELS, exist_ok=True)

# папка для архивных файлов склада
ARCHIVE_DIR_WAREHOUSE = os.path.join(ARCHIVE_DIR, "Warehouse_files")
os.makedirs(ARCHIVE_DIR_WAREHOUSE, exist_ok=True)

# коды подразделения для разделения на потоки обработки
OZON_DIVISION = {19520, "19520"}
OTHER_DIVISION = {16177, "16177"}
YANDEX_DIVISION = {16178, "16178"}

# разрешенные к обработке коды подразделений, для FilePolicy при чтении файлов
ALLOWED_DIVISIONS = {str(x) for x in OZON_DIVISION}
# ALLOWED_DIVISIONS = {
#     str(x) for x in (OZON_DIVISION | OTHER_DIVISION | YANDEX_DIVISION)
# }