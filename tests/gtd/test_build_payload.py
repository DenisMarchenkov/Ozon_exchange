from Confirmations.api.exemplar_status.ozon_gtd_preparation_service import (
    OzonGtdPreparationService
)

def test_build_payload_single_posting():
    service = OzonGtdPreparationService(None, ":memory:")

    exemplars = [
        {"posting_number": "POST-1", "product_id": 100, "exemplar_id": 111},
        {"posting_number": "POST-1", "product_id": 100, "exemplar_id": 222},
    ]

    gtd_map = {
        ("POST-1", 100): "GTD-123"
    }

    payload = service._build_payload(exemplars, gtd_map)

    assert payload == [
        {
            "posting_number": "POST-1",
            "products": [
                {
                    "product_id": 100,
                    "exemplars": [
                        {"exemplar_id": 111, "gtd": "GTD-123"},
                        {"exemplar_id": 222, "gtd": "GTD-123"},
                    ],
                }
            ],
        }
    ]


def test_build_payload_skips_missing_gtd():
    service = OzonGtdPreparationService(None, ":memory:")

    exemplars = [
        {"posting_number": "POST-1", "product_id": 100, "exemplar_id": 111},
    ]

    gtd_map = {}

    payload = service._build_payload(exemplars, gtd_map)

    assert payload == []
