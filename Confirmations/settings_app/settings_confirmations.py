import os

from Common.settings import SUPPLIER_SOURCE, BASE_DIR, ARCHIVE_DIR

CONFIRMATIONS_DIR = os.path.join(SUPPLIER_SOURCE, "Confirmations")
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