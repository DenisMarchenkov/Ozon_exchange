class CatalogLoadError(RuntimeError):
    """Каталог не загружен полностью; использовать его для отправки нельзя."""

    def __init__(self, page_number: int, loaded_count: int, reason: str):
        self.page_number = page_number
        self.loaded_count = loaded_count
        super().__init__(f"страница={page_number}, загружено={loaded_count}; {reason}")
