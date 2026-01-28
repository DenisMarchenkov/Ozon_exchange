MAX_CONCURRENT_REQUESTS = 5

INTERNAL_FINAL_STATUSES = {
    "cancelled",
    "delivered"
}

# маппинг статусов
OZON_TO_INTERNAL_STATUS = {
    "awaiting_packaging": "awaiting_packaging",
    "awaiting_deliver": "awaiting_deliver",
    "delivering": "delivering",
    "driver_pickup": "driver_pickup",
    "delivered": "delivered",
    "cancelled": "cancelled"
}

