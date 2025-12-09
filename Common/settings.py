import os
from dotenv import load_dotenv

# ============================================================
# 🔹 РЕЖИМ РАБОТЫ: DEV / PROD
# ============================================================

DEV_MODE = True   # True → локально, False → VDS


# ============================================================
# 🔹 ЗАГРУЗКА .env
# ============================================================

load_dotenv()   # загружает переменные из .env


# ============================================================
# 🔹 БАЗОВЫЕ ПУТИ ПРОЕКТА
# ============================================================

# .../Ozon_exchange/Common/settings.py
COMMON_DIR = os.path.dirname(os.path.abspath(__file__))

# .../Ozon_exchange
BASE_DIR = os.path.dirname(COMMON_DIR)


# ============================================================
# 🔹 OZON API (ИЗ .env)
# ============================================================

API_TOKEN = os.getenv("OZON_API_TOKEN")
CLIENT_ID = os.getenv("OZON_CLIENT_ID")
WAREHOUSE_ID = os.getenv("OZON_WAREHOUSE_ID")

if not all([API_TOKEN, CLIENT_ID, WAREHOUSE_ID]):
    raise RuntimeError("❌ Не заданы OZON API переменные в .env!")


# ============================================================
# 🔹 ФАЙЛЫ И ПАПКИ ПРОЕКТА
# ============================================================

# Файл с наценками
MARKUP_FILE = os.path.join(BASE_DIR, "Prices", "price change log.xlsx")

# Папка внутри проекта, куда МЫ копируем прайсы поставщика
SUPPLIER_PRICE_FOLDER = os.path.join(BASE_DIR, "Supplier_prices")
os.makedirs(SUPPLIER_PRICE_FOLDER, exist_ok=True)


# ============================================================
# 🔹 FTP / ИСТОЧНИК ПОСТАВЩИКА (DEV / PROD)
# ============================================================

SUPPLIER_PRICE_FILENAME = "stock-update-template_with_price_FD.xls"

if DEV_MODE:
    # 🔧 ЛОКАЛЬНАЯ ЭМУЛЯЦИЯ FTP
    SUPPLIER_SOURCE = r"C:\Users\dmarc\PycharmProjects"
else:
    # 🚀 БОЕВОЙ FTP НА VDS
    SUPPLIER_SOURCE = r"/home/ftp/supplier"


# Исходный файл от поставщика
SUPPLIER_SOURCE_FILE = os.path.join(
    SUPPLIER_SOURCE,
    SUPPLIER_PRICE_FILENAME
)

# Папка заказов (куда формируются DBF)
ORDER_DIR = os.path.join(SUPPLIER_SOURCE, "Orders")
os.makedirs(ORDER_DIR, exist_ok=True)


# ============================================================
# 🔹 НАЦЕНКИ ПО УМОЛЧАНИЮ
# ============================================================

MISSING_DATA_MARKUP = 2.8
MISSING_COEFFICIENT_OLD_PRICE = 0.1
MISSING_COEFFICIENT_MIN_PRICE = 0.05


# ============================================================
# 🔹 CRM / МАГАЗИН
# ============================================================

SHOP_NAME = "Best seller ever"
DIVISION_ID_IN_SUPPLIER_CRM = 10001
CUSTOMER_ID_IN_SUPPLIER_CRM = 101


# ============================================================
# 🔹 БАЗА ДАННЫХ
# ============================================================
DATA_DIR = os.path.join(BASE_DIR, "Data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "storage.db")


# ============================================================
# 🔹 CONFIRMATIONS
# ============================================================

CONFIRMATIONS_DIR = os.path.join(SUPPLIER_SOURCE, "Confirmations")
os.makedirs(CONFIRMATIONS_DIR, exist_ok=True)

# ============================================================
# 🔹 ЗАЩИТА ОТ СЛУЧАЙНОГО PROD НА WINDOWS
# ============================================================

if not DEV_MODE and SUPPLIER_SOURCE.startswith("C:"):
    raise RuntimeError("❌ PROD включён, но путь указывает на Windows!")
