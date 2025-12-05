import json
import os
import shutil
import datetime

from Common.logger import get_logger
from Common.settings import BASE_DIR

logger = get_logger("Common")

def copy_file_with_timestamp(src_file, dest_folder):
    if not os.path.isfile(src_file):
        logger.error(f"Файл '{src_file}' не найден.")
        raise FileNotFoundError(f"Файл '{src_file}' не найден.")

    os.makedirs(dest_folder, exist_ok=True)

    base_name, ext = os.path.splitext(os.path.basename(src_file))
    timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    new_file_name = f"{base_name}_{timestamp}{ext}"
    dest_file = os.path.join(dest_folder, new_file_name)

    shutil.copy2(src_file, dest_file)
    logger.info(f"Скопирован: {src_file} → {dest_file}")
    return dest_file


def get_fake_data(file_name: str) -> dict:
    """Загружает fake-данные из JSON файла в папке tests."""
    path = os.path.join(BASE_DIR, "tests", file_name)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл не найден: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)