from Confirmations.api.exemplar_status.ozon_gtd_preparation_service import (
    OzonGtdPreparationService
)

def test_extract_exemplars_basic():
    service = OzonGtdPreparationService(None, ":memory:")

    ship_data = {
        "key1": {
            "posting_number": "POST-1",
            "products": [
                {
                    "product_id": 100,
                    "exemplars": [
                        {"exemplar_id": 111},
                        {"exemplar_id": 222},
                    ],
                }
            ],
        }
    }

    result = service._extract_exemplars(ship_data)

    assert result == [
        {"posting_number": "POST-1", "product_id": 100, "exemplar_id": 111},
        {"posting_number": "POST-1", "product_id": 100, "exemplar_id": 222},
    ]


def test_extract_exemplars_ignores_broken_data():
    service = OzonGtdPreparationService(None, ":memory:")

    ship_data = {
        "bad": {
            "posting_number": None,
            "products": [],
        }
    }

    result = service._extract_exemplars(ship_data)

    assert result == []
