from dataclasses import dataclass


@dataclass
class UpdateResult:
    """Количество подтвержденных и неподтвержденных обновлений."""

    updated: int = 0
    failed: int = 0

    @property
    def status(self) -> str:
        if self.updated == 0 and self.failed == 0:
            return "SKIPPED"
        if self.failed == 0:
            return "SUCCESS"
        return "PARTIAL" if self.updated else "ERROR"


def ozon_stock_key(item: dict) -> tuple:
    # Настройки из os.getenv содержат строку, JSON-ответ может содержать число.
    warehouse = item.get("warehouse_id")
    return item.get("offer_id"), str(warehouse) if warehouse is not None else None


def confirmed_ozon_stocks(batch: dict, response) -> int:
    if not isinstance(response, dict) or response.get("errors"):
        return 0
    results = response.get("result")
    if not isinstance(results, list):
        return 0

    # Сопоставляем ответы с отправленными товарами и складом.
    # Повторные строки ответа не увеличивают число обновлений.
    confirmed = {
        ozon_stock_key(item)
        for item in results
        if isinstance(item, dict)
        and item.get("updated") is True
        and not item.get("errors")
    }
    return sum(
        ozon_stock_key(item) in confirmed
        for item in batch["stocks"]
    )


def yandex_batch_succeeded(response) -> bool:
    return (
        isinstance(response, dict)
        and response.get("status") == "OK"
        and not response.get("errors")
    )


def promo_batch_succeeded(response) -> bool:
    # V1ProductActionTimerUpdateResponse не содержит полей.
    # Helper возвращает JSON только при HTTP 200; None означает сбой запроса.
    return isinstance(response, dict) and response == {}
