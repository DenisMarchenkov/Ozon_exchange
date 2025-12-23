class DispatchFilesService:
    def __init__(
        self,
        dispatch_repo,
        confirmations_repo,
        labels_generator=None,
        warehouse_builder_cls=None,
        required_file_types: set[str] | None = None,
    ):
        self.dispatch_repo = dispatch_repo
        self.confirmations_repo = confirmations_repo
        self.labels_generator = labels_generator
        self.warehouse_builder_cls = warehouse_builder_cls

        # если не передали — определяем автоматически
        if required_file_types is not None:
            self.required_file_types = required_file_types
        else:
            self.required_file_types = {"WAREHOUSE"}
            if self.labels_generator:
                self.required_file_types.add("LABEL")

    def generate_missing_files(self, dispatch_id: str) -> set[str]:
        dispatch_files = self.dispatch_repo.get_files(dispatch_id)
        present_files = {f["file_type"] for f in dispatch_files}
        missing_files = self.required_file_types - present_files

        if "LABEL" in missing_files and self.labels_generator:
            label_path = self.labels_generator.download(dispatch_id)
            if label_path and label_path.exists():
                self.dispatch_repo.add_file(dispatch_id, "LABEL", label_path)
                missing_files.remove("LABEL")

        if "WAREHOUSE" in missing_files:
            items = self.confirmations_repo.get_items_by_dispatch(dispatch_id)
            if items:
                builder = self.warehouse_builder_cls(rows=items)
                warehouse_path = builder.build()
                if warehouse_path and warehouse_path.exists():
                    self.dispatch_repo.add_file(
                        dispatch_id,
                        "WAREHOUSE",
                        warehouse_path,
                    )
                    missing_files.remove("WAREHOUSE")

        return missing_files

