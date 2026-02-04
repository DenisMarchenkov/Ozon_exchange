import os

from Common.db.database import Database
from Common.db.init_db import init_confirmations_schema, init_dispatch_schema
from Common.file_policy import FilePolicy
from Common.logger import get_logger
from Common.settings import DB_PATH
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.db_confirmations.dispatch_repository import DispatchRepository
from Confirmations.other_flow import run_other_flow

from Confirmations.services.confirmations.confirmations_recorder import ConfirmationsRecorder
from Confirmations.services.confirmations.confirmations_reader import ConfirmationsReader
from Confirmations.services.archive_file_manager import ArchiveFileManager
from Confirmations.services.mailers.mailer_dispatch import DispatchMailer
from Confirmations.services.mailers.mailer_error import ErrorMailer
from Confirmations.services.mailers.mailer_shortage import ShortageMailer
from Confirmations.ozon_flow import run_ozon_flow

from Confirmations.settings_app.settings_confirmations import (
    CONFIRMATIONS_DIR,
    SETTINGS_APP_DIR,
    ARCHIVE_DIR_CONFIRMATIONS, OZON_DIVISION, OTHER_DIVISION, YANDEX_DIVISION, ALLOWED_DIVISIONS,
)
from Confirmations.yandex_flow import run_yandex_flow

logger = get_logger(__name__)



def main():
    logger.info("=== Запуск проверки подтверждений ===")

    # ============================================================
    # 0. DB + REPOSITORIES
    # ============================================================
    db = Database(DB_PATH)
    init_confirmations_schema(db)
    init_dispatch_schema(db)

    confirmations_repo = ConfirmationsRepository(db)
    dispatch_repo = DispatchRepository(db)


    # ============================================================
    # 1. ФИЛЬТРАЦИЯ И ЧТЕНИЕ ПОДТВЕРЖДЕНИЙ
    # ============================================================
    policy = FilePolicy(
        filename_regex=None, # маска файла (регулярное выражение, например r"^[\d-]+_\d+\.xls$")
        ignored_divisions=None, # черный список
        allowed_divisions=ALLOWED_DIVISIONS, # белый список
    )

    reader = ConfirmationsReader(
        folder_path=CONFIRMATIONS_DIR,
        mapping_file=os.path.join(SETTINGS_APP_DIR, "column_map.json"),
        file_policy=policy,
    )
    df = reader.read()


    # ============================================================
    # 2. ЗАПИСЬ В БД
    # ============================================================
    recorder = ConfirmationsRecorder(confirmations_repo)
    recorder.record_from_dataframe(df)


    # ============================================================
    # 3. АРХИВАЦИЯ ФАЙЛОВ
    # ============================================================
    file_manager = ArchiveFileManager(
        inbox_dir=CONFIRMATIONS_DIR,
        archive_dir=ARCHIVE_DIR_CONFIRMATIONS,
        dry_run=False, # True для тестов - не переносим файлы в архив, только логируем
        file_policy=policy,
    )
    file_manager.archive_all()


    # ============================================================
    # 4. ПИСЬМО О НЕХВАТКЕ
    # ============================================================
    refused_items = confirmations_repo.get_items_by_statuses_conf_and_item(
        "awaiting_confirmation", "REFUSED")
    if refused_items:
        logger.warning("Есть отказанные позиции")
        mailer = ShortageMailer(shortage_rows=refused_items)
        mailer.send()
    else:
        logger.info("Нет данных для письма о нехватке товара")


    # ============================================================
    # 5. РАЗДЕЛЕНИЕ ПОДТВЕРЖДЕНИЙ
    # ============================================================
    # confirmed = confirmations_repo.get_by_status("confirmed")
    # error = confirmations_repo.get_by_status("error")
    # ship_not_available = confirmations_repo.get_by_status("ship_not_available")
    # all_confirmations = confirmed + error + ship_not_available

    # confirmed - подтвержденные заказы
    # error - подхватываем которые ранее при обновлении завершились ошибкой
    # ship_not_available - в которых нужно было уточнить гтд, маркировку...
    statuses = ['confirmed', 'error', 'ship_not_available']
    all_confirmations = confirmations_repo.get_by_statuses(statuses)

    ozon_confirmations = [c for c in all_confirmations if c["division_id"] in OZON_DIVISION]
    other_confirmations = [c for c in all_confirmations if c["division_id"] in OTHER_DIVISION]
    yandex_confirmations = [c for c in all_confirmations if c["division_id"] in YANDEX_DIVISION]


    # ============================================================
    # 6. ЗАПУСК СЦЕНАРИЕВ
    # ============================================================
    # ============================================================
    # 6. ЗАПУСК СЦЕНАРИЕВ
    # ============================================================
    # Проверяем, есть ли заказы Ozon, требующие обработки (включая зависшие в awaiting_delivery)
    has_ozon_pending = False
    
    # 1. Новые подтверждения
    if ozon_confirmations:
        has_ozon_pending = True
    
    # 2. Зависшие в ожидании отгрузки (например, если наклейки не сгенерировались)
    if not has_ozon_pending:
        # Проверяем awaiting_delivery только если нет новых, чтобы не делать лишних запросов
        # Но нужно убедиться, что это именно Ozon заказы.
        # В текущей схеме division_id хранится в confirmations.
        # Можно сделать get_by_status("awaiting_delivery"), и отфильтровать по OZON_DIVISION
        pending_delivery = confirmations_repo.get_by_status("awaiting_delivery")
        ozon_pending = [c for c in pending_delivery if c["division_id"] in OZON_DIVISION]
        if ozon_pending:
            logger.info(f"Найдены {len(ozon_pending)} заказов Ozon в ожидании отгрузки. Запускаем flow.")
            has_ozon_pending = True

    if has_ozon_pending:
        logger.info(f"Запуск сценария OZON (новых: {len(ozon_confirmations)})")
        run_ozon_flow(ozon_confirmations, confirmations_repo, dispatch_repo, db)

    if other_confirmations:
        logger.info(f"запуск сценария для {len(other_confirmations)} остальных заказов")
        run_other_flow(other_confirmations, confirmations_repo, dispatch_repo)

    if yandex_confirmations:
        logger.info(f"запуск сценария для {len(yandex_confirmations)} заказов ЯНДЕКС")
        run_yandex_flow(yandex_confirmations, confirmations_repo, dispatch_repo)


    # ============================================================
    # 7. ОТПРАВКА НА СКЛАД ОБРАБОТАННЫХ ДАННЫХ
    # ============================================================
    departures_for_send = dispatch_repo.get_dispatch_id_by_status("PREPARED")

    for dispatch in departures_for_send:
        d_id = dispatch.get("id")

        try:
            dispatch_files = dispatch_repo.get_files(d_id)
            processing_orders = confirmations_repo.get_postings_by_dispatch(d_id)
            if not dispatch_files:
                raise RuntimeError("Нет файлов для отправки")

            mailer = DispatchMailer(dispatch_files, processing_orders)
            mailer.send()

            dispatch_repo.update_status(d_id, "SHIPPED_TO_STOCK")

        except Exception:
            logger.exception(f"Ошибка отправки dispatch {d_id}")
            dispatch_repo.update_status(d_id, "ERROR")


    # ============================================================
    # 8. ПИСЬМО О ЗАКАЗАХ СО СТАТУСОМ "ERROR" ПОСЛЕ ОБМЕНА
    # ============================================================
    remaining_errors = confirmations_repo.get_by_status("error")
    if remaining_errors:
        logger.warning("После обмена данными стались заказы со статусом [error]")
        mailer = ErrorMailer(error_rows=remaining_errors)
        mailer.send()

    logger.info("=== Проверка подтверждений завершена ===")


if __name__ == "__main__":
    main()
