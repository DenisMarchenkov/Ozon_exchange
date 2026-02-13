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


def build_gtd_absent_structure(full_status_resp: dict, status: str = "ship_not_available") -> dict:
    """
    Преобразует ответ Ozon в структуру с флагами GTD для каждого экземпляра.

    Args:
        full_status_resp (dict): Ответ Ozon от get_full_exemplar_status(posting_number)
        status (str): Статус отправления, по умолчанию "ship_available"

    Returns:
        dict: Структура вида:
            {
                "posting_number": str,
                "products": [
                    {
                        "product_id": int,
                        "exemplars": [
                            {
                                "exemplar_id": int,
                                "gtd": str,
                                "gtd_check_status": str,
                                "gtd_error_codes": list,
                                "is_gtd_absent": bool,
                                "is_rnpt_absent": bool,
                                "marks": list,
                                "rnpt": str,
                                "rnpt_check_status": str,
                                "rnpt_error_codes": list,
                                "weight": float,
                                "weight_check_status": str,
                                "weight_error_codes": list
                            },
                            ...
                        ]
                    },
                    ...
                ],
                "status": str
            }
    """
    posting_number = full_status_resp.get("posting_number", "")
    products_list = []

    for product in full_status_resp.get("products", []):
        # Только если GTD нужен, иначе можно пропустить
        if product.get("is_gtd_needed", False):
            product_entry = {
                "product_id": product.get("product_id"),
                "exemplars": []
            }

            for ex in product.get("exemplars", []):
                exemplar_entry = {
                    "exemplar_id": ex.get("exemplar_id"),
                    "gtd": ex.get("gtd", ""),
                    "gtd_check_status": "",
                    "gtd_error_codes": [],
                    "is_gtd_absent": True,  # ставим True, если нужно GTD
                    "is_rnpt_absent": ex.get("is_rnpt_absent", False),
                    "marks": ex.get("marks", []),
                    "rnpt": ex.get("rnpt", ""),
                    "rnpt_check_status": "",
                    "rnpt_error_codes": [],
                    "weight": ex.get("weight", 0),
                    "weight_check_status": "",
                    "weight_error_codes": []
                }
                product_entry["exemplars"].append(exemplar_entry)

            products_list.append(product_entry)

    return {
        "posting_number": posting_number,
        "products": products_list,
        "status": status
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
