import os
from dotenv import load_dotenv

# ============================================================
# 🔹 РЕЖИМ РАБОТЫ: DEV / PROD
# ============================================================
DEV_MODE = True   # True → локально, False → VDS


# ============================================================
# 🔹 НАСТРОЙКИ МАГАЗИНА
# ============================================================
SUPPLIER_ID = "10001" # ДИСТРИФАРМ - внутренний ID, не используется (задел на будущее)
NAME_SHOP = "Farmaderm"
SHORT_NAME_SHOP = "FD"


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

# .../Ozon_exchange/Archive
ARCHIVE_DIR = os.path.join(BASE_DIR, "Archive")

# ============================================================
# 🔹 OZON API (ИЗ .env)
# ============================================================
if DEV_MODE:
    API_TOKEN = "fasfaf"
    CLIENT_ID = "afdasf"
    WAREHOUSE_ID = "fsdfsadf"
else:
    API_TOKEN = os.getenv("OZON_API_TOKEN")
    CLIENT_ID = os.getenv("OZON_CLIENT_ID")
    WAREHOUSE_ID = os.getenv("OZON_WAREHOUSE_ID")

if not all([API_TOKEN, CLIENT_ID, WAREHOUSE_ID]):
    raise RuntimeError("❌ Не заданы OZON API переменные в .env!")


# ============================================================
# 🔹 YANDEX API (ИЗ .env)
# ============================================================
if DEV_MODE:
    # YANDEX_API_TOKEN = "test_yandex_token"
    # YANDEX_BUSINESS_ID = "test_yandex_business_id"
    YANDEX_API_TOKEN = "ACMA:US3OObmytXCfR17WGPO1aEeO0bjoWXEkVUCDUJMt:484197b6"
    YANDEX_BUSINESS_ID = "835879"
else:
    YANDEX_API_TOKEN = os.getenv("YANDEX_API_TOKEN")
    YANDEX_BUSINESS_ID = os.getenv("YANDEX_BUSINESS_ID")

if not all([YANDEX_API_TOKEN, YANDEX_BUSINESS_ID]):
    raise RuntimeError("❌ Не заданы YANDEX API переменные в .env!")


# ============================================================
# 🔹 ФАЙЛЫ И ПАПКИ ПРОЕКТА
# ============================================================
# Папка внутри проекта, куда МЫ копируем прайсы поставщика
SUPPLIER_PRICE_FOLDER = os.path.join(ARCHIVE_DIR, "Supplier_prices")
os.makedirs(SUPPLIER_PRICE_FOLDER, exist_ok=True)


# ============================================================
# 🔹 FTP / ИСТОЧНИК ПОСТАВЩИКА (DEV / PROD)
# ============================================================
#FTP_PATH = "/srv/ftpdata"

if DEV_MODE:
    # 🔧 ЛОКАЛЬНАЯ ЭМУЛЯЦИЯ FTP
    FTP_PATH = r"C:\Users\dmarc\PycharmProjects"
    SUPPLIER_SOURCE = r"C:\Users\dmarc\PycharmProjects"
else:
    # 🚀 БОЕВОЙ FTP НА VDS
    FTP_PATH = "/srv/ftpdata"
    SUPPLIER_SOURCE = os.path.join(FTP_PATH, "Prices", NAME_SHOP)


# Исходный файл от поставщика
SUPPLIER_PRICE_FILENAME = "price_farmaderm.xls"
SUPPLIER_SOURCE_FILE = os.path.join(SUPPLIER_SOURCE, SUPPLIER_PRICE_FILENAME)


# ============================================================
# 🔹 БАЗА ДАННЫХ
# ============================================================
DATA_DIR = os.path.join(BASE_DIR, "Data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "storage.db")


# ============================================================
# 🔹 НАСТРОЙКИ ДЛЯ РАБОТЫ С ПОЧТОЙ
# ============================================================
MAILER_SERVER_IMAP = "imap.yandex.ru"
MAILER_PORT_IMAP = "993"
MAILER_SERVER_SMTP = "smtp.yandex.ru"
MAILER_PORT_SMTP = "465"
MAILER_LOGIN = os.getenv("MAILER_LOGIN")
MAILER_PASSWORD = os.getenv("MAILER_PASSWORD_API")
RECIPIENT_ADMIN = ["DenisMarchenkov@dfarm.ru", "blinkin@dfarm.ru", "sklad@frenchpharmacy.ru"]


# ============================================================
# 🔹 ЗАЩИТА ОТ СЛУЧАЙНОГО PROD НА WINDOWS
# ============================================================
if not DEV_MODE and SUPPLIER_SOURCE.startswith("C:"):
    raise RuntimeError("❌ PROD включён, но путь указывает на Windows!")
