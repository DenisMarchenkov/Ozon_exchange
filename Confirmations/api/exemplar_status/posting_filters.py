def filter_postings_with_gtd_absent(postings: dict) -> dict:
    """
    Оставляет только отправления OZON, в которых нужно уточнить ГТД.
    """
    return {
        posting_number: posting
        for posting_number, posting in postings.items()
        if any(
            exemplar.get("is_gtd_absent") is True
            for product in posting.get("products", [])
            for exemplar in product.get("exemplars", [])
        )
    }


def filter_postings_requiring_mandatory_marking(postings: dict) -> dict:
    """
    Возвращает отправления, для которых требуется обновление обязательной
    маркировки «Честный ЗНАК» (mark_type = mandatory_mark).

    Критерий:
    - код маркировки отсутствует;
    - или проверка не пройдена (check_status != 'passed');
    - или есть ошибки проверки.
    """
    result = {}

    for posting_number, posting in postings.items():
        for product in posting.get("products", []):
            for exemplar in product.get("exemplars", []):
                for mark in exemplar.get("marks", []):
                    if mark.get("mark_type") != "mandatory_mark":
                        continue

                    if (
                        not mark.get("mark")
                        or mark.get("check_status") != "passed"
                        or mark.get("error_codes")
                    ):
                        result[posting_number] = posting
                        break
                else:
                    continue
                break
            else:
                continue
            break

    return result
