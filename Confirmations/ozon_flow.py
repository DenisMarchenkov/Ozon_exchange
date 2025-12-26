from pprint import pprint

from Common.logger import get_logger
from Confirmations.services.confirmations.confirmations_status_updater import ConfirmationsStatusUpdater
from Confirmations.services.confirmations.exemplar_ship_availability import ExemplarShipAvailabilityService
from Confirmations.services.dispatch.DispatchRetryService import DispatchRetryService
from Confirmations.services.dispatch.DispatchPrepareService import DispatchPrepareService
from Confirmations.services.dispatch.DispatchFilesService import DispatchFilesService
from Confirmations.services.labels.labels_generatior import LabelsGenerator
from Confirmations.services.warehouse_file_builder import WarehouseFileBuilder

from Common.time import now_iso

logger = get_logger(__name__)


def run_ozon_flow(ozon_confirmations, confirmations_repo, dispatch_repo):
    """
    Запуск OZON-сценария.

    :param ozon_confirmations: список словарей с подтверждениями только для OZON
    :param confirmations_repo: репозиторий подтверждений
    :param dispatch_repo: репозиторий dispatch
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
        pprint(ship_not_available)
        # TODO обновить необходимые данные в озон
        # это структура для обновления гтд в запросе https://api-seller.ozon.ru/v6/fbs/posting/product/exemplar/set
        # {
        #     "posting_number": "30229416-0491-3",
        #     "products": [
        #         {
        #             "exemplars": [
        #                 {
        #                     "exemplar_id": 27100664968,
        #                     "gtd": "10132160/191125/5229689/22"
        #                 }
        #             ],
        #             "product_id": 2042205041
        #         }
        #     ]
        # }

        # TODO отправить письмо что с заказами косяк




    # ============================================================
    # 3. DISPATCH: RETRY → PREPARE
    # ============================================================
    labels_generator = LabelsGenerator()
    files_service = DispatchFilesService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        labels_generator=labels_generator,
        warehouse_builder_cls=lambda rows: WarehouseFileBuilder(rows, suffix="OZON"),
    )

    # --- retry ERROR dispatch ---
    retry_service = DispatchRetryService(
        dispatch_repo=dispatch_repo,
        files_service=files_service,
    )
    retry_service.retry_failed()

    # --- prepare новый dispatch с блокировкой только OZON-подтверждений ---
    dispatch_id = f"dispatch_{now_iso()}_OZON"
    prepare_service = DispatchPrepareService(
        dispatch_repo=dispatch_repo,
        confirmations_repo=confirmations_repo,
        files_service=files_service,
    )

    prepare_service.prepare(dispatch_id)

    logger.info(f"Dispatch {dispatch_id} завершён")