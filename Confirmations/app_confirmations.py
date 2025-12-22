import os
from Common.logger import get_logger
from Common.settings import DB_PATH
from Confirmations.db_confirmations.confirmations_repository import ConfirmationsRepository
from Confirmations.db_confirmations.dispatch_repository import DispatchRepository

from Confirmations.services.confirmations.confirmations_recorder import ConfirmationsRecorder
from Confirmations.services.confirmations.confirmations_reader import ConfirmationsReader
from Confirmations.services.archive_file_manager import ArchiveFileManager
from Confirmations.services.mailers.mailer_dispatch import DispatchMailer

from Confirmations.ozon_flow import run_ozon_flow

from Confirmations.settings_app.settings_confirmations import (
    CONFIRMATIONS_DIR,
    SETTINGS_APP_DIR,
    ARCHIVE_DIR_CONFIRMATIONS, OZON_DIVISION,
)

logger = get_logger(__name__)



def main():
    logger.info("=== Запуск проверки подтверждений ===")

    # ============================================================
    # 1. ЧТЕНИЕ ПОДТВЕРЖДЕНИЙ
    # ============================================================
    reader = ConfirmationsReader(
        folder_path=CONFIRMATIONS_DIR,
        mapping_file=os.path.join(SETTINGS_APP_DIR, "column_map.json"),
    )
    df = reader.read()

    # ============================================================
    # 2. ЗАПИСЬ В БД
    # ============================================================
    confirmations_repo = ConfirmationsRepository(DB_PATH)
    recorder = ConfirmationsRecorder(confirmations_repo)
    recorder.record_from_dataframe(df)

    # ============================================================
    # 3. АРХИВАЦИЯ ФАЙЛОВ
    # ============================================================
    file_manager = ArchiveFileManager(
        inbox_dir=CONFIRMATIONS_DIR,
        archive_dir=ARCHIVE_DIR_CONFIRMATIONS,
        dry_run=True,
    )
    file_manager.archive_all()

    # ============================================================
    # 4. РАЗДЕЛЕНИЕ ПОДТВЕРЖДЕНИЙ
    # ============================================================
    #all_confirmations = confirmations_repo.get_all()
    all_confirmations = confirmations_repo.get_by_status("confirmed")

    ozon_confirmations = [c for c in all_confirmations if c["division_id"] in OZON_DIVISION]
    other_confirmations = [c for c in all_confirmations if c["division_id"] not in OZON_DIVISION]

    dispatch_repo = DispatchRepository(DB_PATH)


    # ============================================================
    # 5. ЗАПУСК СЦЕНАРИЕВ
    # ============================================================
    if ozon_confirmations:
        logger.info(f"запуск сценария для {len(ozon_confirmations)} заказов ОЗОН")
        run_ozon_flow(ozon_confirmations, confirmations_repo ,dispatch_repo)

    if other_confirmations:
        logger.info(f"запуск сценария для {len(other_confirmations)} остальных заказов")
        #run_other_flow(other_confirmations, dispatch_repo)


    # ============================================================
    # 6. ОТПРАВКА НА СКЛАД
    # ============================================================
    departures_for_send = dispatch_repo.get_dispatch_id_by_status("PREPARED")

    for dispatch in departures_for_send:
        d_id = dispatch.get("id")

        try:
            dispatch_files = dispatch_repo.get_files(d_id)
            if not dispatch_files:
                raise RuntimeError("Нет файлов для отправки")

            mailer = DispatchMailer(dispatch_files)
            mailer.send()

            dispatch_repo.update_status(d_id, "SHIPPED_TO_STOCK")

        except Exception:
            logger.exception(f"Ошибка отправки dispatch {d_id}")
            dispatch_repo.update_status(d_id, "ERROR")

    logger.info("=== Проверка подтверждений завершена ===")


if __name__ == "__main__":
    main()


    repo_conf = ConfirmationsRepository(DB_PATH)
    repo_disp = DispatchRepository(DB_PATH)
    row = repo_conf.get_all()

    for r in row:
        print(r)
    print("--------------------------------------------")

    row = repo_conf.get_all_items()
    for r in row:
        print(r)
    print("--------------------------------------------")

    row = repo_disp.get_all_dispatch()
    for r in row:
        print(r)
    print("--------------------------------------------")

    row = repo_disp.get_all_files()
    for r in row:
        print(r)
    print("--------------------------------------------")