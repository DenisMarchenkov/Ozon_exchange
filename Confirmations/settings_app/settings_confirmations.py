import os

from Common.settings import SUPPLIER_SOURCE, BASE_DIR

CONFIRMATIONS_DIR = os.path.join(SUPPLIER_SOURCE, "Confirmations")
os.makedirs(CONFIRMATIONS_DIR, exist_ok=True)

# папка с приложением
APP_DIR = os.path.join(BASE_DIR, "Confirmations")

# папка с настройками для приложения
SETTINGS_APP_DIR = os.path.join(APP_DIR, "settings_app")