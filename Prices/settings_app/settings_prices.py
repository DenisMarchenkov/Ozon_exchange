# Файл с наценками
import os

from Common.settings import BASE_DIR

# папка с приложением
APP_DIR = os.path.join(BASE_DIR, "Prices")

# папка с настройками для приложения
SETTINGS_APP_DIR = os.path.join(APP_DIR, "settings_app")


# файл с наценками
MARKUP_FILE = os.path.join(SETTINGS_APP_DIR, "price change log.xlsx")

# Наценки по умолчанию
MISSING_DATA_MARKUP = 2.8
MISSING_COEFFICIENT_OLD_PRICE = 0.1
MISSING_COEFFICIENT_MIN_PRICE = 0.05