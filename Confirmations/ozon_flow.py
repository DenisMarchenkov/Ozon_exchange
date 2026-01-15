from Common.time import now_iso
from Common.logger import get_logger
from Confirmations.api.exemplar_status.posting_filters import filter_postings_with_gtd_absent, \
    filter_postings_requiring_mandatory_marking
from Confirmations.services.dispatch.DispatchRetryService import DispatchRetryService
from Confirmations.services.dispatch.DispatchPrepareService import DispatchPrepareService
from Confirmations.services.dispatch.DispatchFilesService import DispatchFilesService
from Confirmations.services.labels.ozon_labels_generator import LabelsGenerator
from Confirmations.services.mailers.mailer_gtd_update import GTDAutoUpdateMailer
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
    if not ozon_confirmations:
        logger.info("Нет подтверждений для OZON")
        return


    # ============================================================
    # 1. ПРОВЕРКА ЗАКАЗОВ НА ДОСТУПНОСТЬ К СБОРКЕ
    # ============================================================
    service = ExemplarShipAvailabilityService()
    postings = service.divide_postings(ozon_confirmations)
    ship_available = postings["ship_available"]
    ship_not_available = postings["ship_not_available"]


    # ============================================================
    # 2. ОБНОВЛЕНИЕ СТАТУСОВ OZON
    # ============================================================
    # для разрешенных отправлений
    if ship_available:
        logger.info(f"Одобренные для ship: {len(ship_available)}")
        updater = ConfirmationsStatusUpdater()
        updater.process_deliveries(list(ship_available.keys()))
    else:
        logger.info("Нет данных для обновления статусов заказов в OZON")

    # для не разрешенных отправлений
    if ship_not_available:
        logger.info(f"НЕ одобренные для ship: {len(ship_not_available)}")
        for ship in list(ship_not_available.keys()):
            confirmations_repo.update_status(ship, "ship_not_available")

        # оставляем только отправления, для которых отсутствуют данные ГТД
        is_gtd_absent_postings = filter_postings_with_gtd_absent(ship_not_available)
        # оставляем только отправления, для которых отсутствуют коды маркировке "Честный знак"
        is_gtd_absent_marking = filter_postings_requiring_mandatory_marking(ship_not_available)

        # обновить данные ГТД в озон
        gtd_repo = GtdRepository(db)
        gtd_service = OzonGtdPreparationService(gtd_repo=gtd_repo)
        payloads = gtd_service.prepare(is_gtd_absent_postings)

        ozon_client = OzonGtdUpdater()
        for payload in payloads:
            ozon_client.update_gtd(payload)

        # обновить коды маркировки в озон
        # использовать is_gtd_absent_marking


    # ============================================================
    # 3. Письмо о попытке обновить данные экземпляров отправления (ГТД)
    # ============================================================
    update_gtd_data = confirmations_repo.get_by_status("ship_not_available")
    if update_gtd_data:
        mailer = GTDAutoUpdateMailer(update_gtd_data)
        mailer.send()


    # ============================================================
    # 4. Инициализация генератора ярлыков
    # ============================================================
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

    prepare_service.prepare(dispatch_id)

    logger.info(f"Dispatch {dispatch_id} завершён")