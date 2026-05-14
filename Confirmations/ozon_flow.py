import time

from Common.settings import RECIPIENT_MANAGERS
from Common.time import now_iso
from Common.logger import get_logger
from Confirmations.api.exemplar_status.posting_filters import filter_postings_with_gtd_absent, \
    filter_postings_requiring_mandatory_marking, build_gtd_absent_structure
from Confirmations.services.dispatch.DispatchRetryService import DispatchRetryService
from Confirmations.services.dispatch.DispatchPrepareService import DispatchPrepareService
from Confirmations.services.dispatch.DispatchFilesService import DispatchFilesService
from Confirmations.services.labels.ozon_labels_generator import LabelsGenerator
from Confirmations.services.mailers.mailer_gtd_update import GTDAutoUpdateMailer
from Confirmations.services.mailers.mailer_marking_update import MarkingAutoUpdateMailer
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder
from Confirmations.services.confirmations.confirmations_status_updater import ConfirmationsStatusUpdater
from Confirmations.api.exemplar_status.exemplar_ship_availability import ExemplarShipAvailabilityService
from Confirmations.api.exemplar_status.ozon_gtd_preparation_service import (OzonGtdPreparationService, GtdRepository,
                                                                            OzonGtdUpdater)

logger = get_logger(__name__)


def run_ozon_flow(ozon_confirmations, confirmations_repo, dispatch_repo, db):
    """
    Запуск OZON-сценария.

    :param ozon_confirmations: список словарей с подтверждениями только для OZON
    :param confirmations_repo: репозиторий подтверждений
    :param dispatch_repo: репозиторий dispatch
    :param db экземпляр Database, используемый для доступа к SQLite-базе
    """
    if ozon_confirmations:
        # ============================================================
        # 1. ПРОВЕРКА ЗАКАЗОВ НА ДОСТУПНОСТЬ К СБОРКЕ
        # ============================================================
        service = ExemplarShipAvailabilityService()
        postings = service.divide_postings(ozon_confirmations)
        ship_available = postings["ship_available"]
        ship_not_available = postings["ship_not_available"]


        # 2. ОБНОВЛЕНИЕ СТАТУСОВ OZON
        # ============================================================
        # Логируем все категории, чтобы не было "слепых зон"
        for category, items in postings.items():
            if items and category not in ["ship_available", "ship_not_available"]:
                logger.info(f"Заказы в категории '{category}': {len(items)}")
                logger.info(f"Список {category}: {list(items.keys())}")

        # для разрешенных отправлений
        if ship_available:
            logger.info(f"Одобренные для ship: {len(ship_available)}")
            updater = ConfirmationsStatusUpdater()
            updater.process_deliveries(list(ship_available.keys()))
        else:
            logger.info("Нет новых заказов, готовых к сборке (ship_available) в OZON")

        # для не разрешенных отправлений
        if ship_not_available:
            logger.info(f"НЕ одобренные для ship (требуют ГТД/маркировку): {len(ship_not_available)}")
            logger.info(f"Список ship_not_available: {list(ship_not_available.keys())}")

            # Обновляем статус "ship_not_available"
            for ship in ship_not_available:
                confirmations_repo.update_status(ship, "ship_not_available")

            # Формируем структуру для GTD
            is_gtd_absent = {}
            for posting_number in ship_not_available:
                full_status_resp = service.api.get_full_exemplar_status(posting_number)
                structured = build_gtd_absent_structure(full_status_resp)
                is_gtd_absent[posting_number] = structured

            # Обновляем статус "is_gtd_absent" в БД
            for posting_number in is_gtd_absent:
                confirmations_repo.update_status(posting_number, "is_gtd_absent")

            # Обновляем данные GTD в Ozon
            if is_gtd_absent:
                gtd_repo = GtdRepository(db)
                gtd_service = OzonGtdPreparationService(gtd_repo=gtd_repo)
                payloads = gtd_service.prepare(is_gtd_absent)

                ozon_client = OzonGtdUpdater()
                for payload in payloads:
                    try:
                        ozon_client.update_gtd(payload)
                        time.sleep(0.1)
                    except Exception as e:
                        logger.error(f"[GTD_UPDATE] Ошибка обновления GTD для {payload.get('posting_number')}: {e}")



            # оставляем только отправления, для которых отсутствуют коды маркировке "Честный знак"
            is_marking_absent = filter_postings_requiring_mandatory_marking(ship_not_available)
            for ship in list(is_marking_absent.keys()):
                confirmations_repo.update_status(ship, "is_marking_absent")
            # todo обновить коды маркировки в озон используя is_marking_absent. Написать OzonGtdPreparationService


        # ============================================================
        # 3. Письмо о попытке обновить данные экземпляров отправления (ГТД и маркировка)
        # ============================================================
        update_gtd_data = confirmations_repo.get_by_status("is_gtd_absent")
        if update_gtd_data:
            mailer = GTDAutoUpdateMailer(update_gtd_data, to=RECIPIENT_MANAGERS)
            mailer.send()

        update_marking_data = confirmations_repo.get_by_status("is_marking_absent")
        if update_marking_data:
            mailer = MarkingAutoUpdateMailer(update_marking_data)
            mailer.send()
    else:
        logger.info("Нет НОВЫХ подтверждений для OZON (пропуск обновления статусов)")


    # ============================================================
    # 4. Инициализация генератора ярлыков
    # ============================================================
    time.sleep(10) # задержка, что бы озон успел обновить у себя данные после перевода заказов в "ожидает отгрузки"
    labels_generator = LabelsGenerator()


    # ============================================================
    # 5. Инициализация файлового сервиса Dispatch
    # ============================================================
    files_service = DispatchFilesService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        labels_generator=labels_generator,
        warehouse_builder_cls=lambda rows: WarehouseFileBuilder(rows, suffix="OZON"),
    )

    # ============================================================
    # 6. Retry failed dispatch
    # ============================================================
    retry_service = DispatchRetryService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service,
    )
    retry_service.retry_failed()

    # ============================================================
    # 7. Prepare новый dispatch с блокировкой только OZON-подтверждений
    # ============================================================
    dispatch_id = f"dispatch_{now_iso()}_OZON"
    prepare_service = DispatchPrepareService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service,
    )

    from Confirmations.settings_app.settings_confirmations import OZON_DIVISION
    prepare_service.prepare(dispatch_id, divisions=tuple(OZON_DIVISION))

    logger.info(f"Dispatch {dispatch_id} завершён")