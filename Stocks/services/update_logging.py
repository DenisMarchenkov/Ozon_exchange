from Stocks.services.update_result import ozon_stock_key


def response_reason(response, expected: str) -> str:
    """Краткая диагностика ответа без заголовков и тела запроса."""
    if response is None:
        return "ответ API не получен; подробности сетевой/HTTP ошибки см. выше"
    if not isinstance(response, dict):
        return f"неожиданный тип ответа: {type(response).__name__}; ожидалось {expected}"
    if response.get("errors"):
        return f"ошибки API: {str(response['errors'])[:2000]}"
    if response.get("message") or response.get("code"):
        return f"код={response.get('code')!r}, сообщение={str(response.get('message', ''))[:2000]}"
    return (
        f"нет подтверждения {expected}; status={response.get('status')!r}, "
        f"тип result={type(response.get('result')).__name__}, "
        f"result={response.get('result') if isinstance(response.get('result'), bool) else 'не подтвержден'}"
    )


def log_ozon_failures(logger, batch: dict, response, batch_number: int):
    items = response.get("result") if isinstance(response, dict) else None
    if not isinstance(items, list) or response.get("errors"):
        logger.error(
            "Ozon: партия %s, не подтверждено %s товаров, offer_ids=%s; причина: %s",
            batch_number, len(batch["stocks"]),
            [item["offer_id"] for item in batch["stocks"]],
            response_reason(response, "result со списком результатов товаров"),
        )
        return

    index = {}
    for item in items:
        if isinstance(item, dict):
            key = ozon_stock_key(item)
            try:
                hash(key)
            except TypeError:
                continue
            index.setdefault(key, []).append(item)

    for stock in batch["stocks"]:
        matches = index.get(ozon_stock_key(stock), [])
        if any(item.get("updated") is True and not item.get("errors") for item in matches):
            continue
        reason = "в ответе нет результата для товара и склада"
        if matches:
            reason = "; ".join(
                f"updated={item.get('updated')!r}, errors={str(item.get('errors', []))[:2000]}"
                for item in matches
            )
        logger.error(
            "Ozon: партия %s, offer_id=%s, warehouse_id=%s, stock=%s; причина: %s",
            batch_number, stock["offer_id"], stock["warehouse_id"], stock["stock"], reason,
        )


def log_update_result(logger, operation: str, result, session_id=None):
    level = logger.error if result.status == "ERROR" else (
        logger.warning if result.status == "PARTIAL" else logger.info
    )
    level(
        "%s: status=%s, session_id=%s, подтверждено=%s, не подтверждено=%s",
        operation, result.status, session_id, result.updated, result.failed,
    )
