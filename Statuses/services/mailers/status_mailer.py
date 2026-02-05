from typing import List, Dict
from Common.base_mailer import BaseMailer

# class StatusMailer(BaseMailer):
#     """
#     Письмо об изменении статусов заказов на маркетплейсе.
#     """
#
#     def __init__(self, changes: List[Dict[str, str]], *args, **kwargs):
#         """
#         :param changes: список словарей вида {"posting_number": str, "old_status": str, "new_status": str}
#         :param args, kwargs: передаются в BaseMailer
#         """
#         super().__init__(*args, **kwargs)
#         self.changes = changes
#
#     def build_subject_core(self) -> str:
#         return f"Изменение статусов заказов ({len(self.changes)} шт.)"
#
#     def build_body(self) -> str:
#         if not self.changes:
#             return "Добрый день!\n\nИзменений статусов за этот период не зафиксировано.\n"
#
#         # Сортировка по новому статусу
#         sorted_changes = sorted(self.changes, key=lambda x: x['new_status'])
#
#         has_cancelled = any(c['new_status'] == 'cancelled' for c in sorted_changes)
#
#         body_lines = ["Добрый день!\n"]
#
#         if has_cancelled:
#             body_lines.append("!!! ВНИМАНИЕ: ОБНАРУЖЕНЫ ОТМЕНЕННЫЕ ЗАКАЗЫ !!!")
#             body_lines.append("Пожалуйста, проверьте список ниже и примите меры.\n")
#
#         body_lines.append("Зафиксированы изменения статусов заказов на маркетплейсе Ozon:\n")
#         body_lines.append(f"{'Номер заказа':<25} | {'Старый статус OZON':<25} | {'Новый статус OZON':<25} | {'Внутр. статус':<20}")
#         body_lines.append("-" * 105)
#
#         for change in sorted_changes:
#             old_st = change['old_status'] or 'NEW'
#             new_st = change['new_status']
#             int_st = change.get('internal_status', '---')
#             line = f"{change['posting_number']:<25} | {old_st:<25} | {new_st:<25} | {int_st:<20}"
#             body_lines.append(line)
#
#         # Добавляем справку по статусам
#         body_lines.append("\n" * 3)
#         body_lines.append("\n" + "="*40)
#         body_lines.append("СПРАВОЧНИК СТАТУСОВ")
#         body_lines.append("="*40)
#
#         body_lines.append("\n--- Внутренние статусы (наша система) ---")
#         body_lines.append("NEW                    - Заказ только что импортирован из файла")
#         body_lines.append("confirmed              - Подтвержден офисом, готов к передаче в Ozon")
#         body_lines.append("awaiting_confirmation  - Есть отказы по позициям, нужно подтверждение офиса")
#         body_lines.append("ship_not_available     - Ozon временно отклонил сборку заказа")
#         body_lines.append("is_gtd_absent          - Не заполнены номера ГТД")
#         body_lines.append("is_marking_absent      - Не заполнены коды маркировки (Честный Знак)")
#         body_lines.append("awaiting_delivery      - Заказ успешно передан в сборку на стороне Ozon")
#         body_lines.append("error                  - Ошибка при попытке собрать заказ через API")
#         body_lines.append("IN_DISPATCH            - Заказ включен в задание для склада")
#         body_lines.append("READY_FOR_SHIPMENT     - Заказ полностью подготовлен системой и ожидает сборки на складе")
#
#         body_lines.append("\n--- Статусы маркетплейса (Ozon) ---")
#         body_lines.append("NOT_VERIFIED           - заказ только создан и ещё не проходил проверку")
#         body_lines.append("awaiting_packaging     - ожидает упаковки")
#         body_lines.append("awaiting_deliver       - заказ собран и ожидает отгрузки")
#         body_lines.append("delivering             - доставляется")
#         body_lines.append("driver_pickup          - передан водителю для доставки")
#         body_lines.append("cancelled              - отменено")
#         body_lines.append("delivered              - доставлен")
#         body_lines.append("not_accepted           - не принят на сортировочном центре")
#         body_lines.append("awaiting_registration  - ожидает регистрации")
#         body_lines.append("awaiting_approve       - ожидает подтверждения")
#         body_lines.append("client_arbitration     - клиентский арбитраж доставки")
#         body_lines.append("arbitration            - арбитраж")
#         body_lines.append("acceptance_in_progress - идёт приёмка")
#
#         return "\n".join(body_lines)


class StatusMailer(BaseMailer):
    """
    Письмо об изменении статусов заказов Ozon.
    Plain-text + HTML.
    """

    # -------------------- справочники --------------------

    INTERNAL_STATUSES = [
        ("NEW", "Заказ только что импортирован из файла"),
        ("confirmed", "Подтверждён офисом, готов к передаче в Ozon"),
        ("awaiting_confirmation", "Есть отказы по позициям, требуется подтверждение офиса"),
        ("ship_not_available", "Ozon временно отклонил сборку заказа"),
        ("is_gtd_absent", "Не заполнены номера ГТД"),
        ("is_marking_absent", "Не заполнены коды маркировки (Честный Знак)"),
        ("awaiting_delivery", "Заказ передан в сборку на стороне Ozon"),
        ("error", "Ошибка при попытке собрать заказ через API"),
        ("IN_DISPATCH", "Заказ включён в задание для склада"),
        ("READY_FOR_SHIPMENT", "Полностью подготовлен и ожидает сборки на складе"),
    ]

    OZON_STATUSES = [
        ("NOT_VERIFIED", "Заказ создан и ещё не проходил проверку"),
        ("awaiting_packaging", "Ожидает упаковки"),
        ("awaiting_deliver", "Ожидает отгрузки"),
        ("delivering", "Доставляется"),
        ("driver_pickup", "Передан водителю для доставки"),
        ("cancelled", "Отменён"),
        ("delivered", "Доставлен"),
        ("not_accepted", "Не принят на сортировочном центре"),
        ("awaiting_registration", "Ожидает регистрации"),
        ("awaiting_approve", "Ожидает подтверждения"),
        ("client_arbitration", "Клиентский арбитраж доставки"),
        ("arbitration", "Арбитраж"),
        ("acceptance_in_progress", "Идёт приёмка"),
    ]

    # ----------------------------------------------------

    def __init__(self, changes: List[Dict[str, str]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.changes = changes

    def build_subject_core(self) -> str:
        return f"Изменение статусов заказов ({len(self.changes)} шт.)"

    # ==================== TEXT ====================

    def build_body(self) -> str:
        if not self.changes:
            return "Добрый день!\n\nИзменений статусов за этот период не зафиксировано.\n"

        sorted_changes = sorted(self.changes, key=lambda x: x["new_status"])
        has_cancelled = any(c["new_status"] == "cancelled" for c in sorted_changes)

        lines = ["Добрый день!\n"]

        if has_cancelled:
            lines.append("!!! ВНИМАНИЕ: ОБНАРУЖЕНЫ ОТМЕНЕННЫЕ ЗАКАЗЫ !!!\n")

        # --- таблица изменений ---
        lines.append(
            f"{'Номер заказа':<25} | "
            f"{'Старый статус OZON':<25} | "
            f"{'Новый статус OZON':<25} | "
            f"{'Внутр. статус':<20}"
        )
        lines.append("-" * 105)

        for c in sorted_changes:
            lines.append(
                f"{c['posting_number']:<25} | "
                f"{(c['old_status'] or 'NEW'):<25} | "
                f"{c['new_status']:<25} | "
                f"{c.get('internal_status', '---'):<20}"
            )

        # --- справочник статусов (через константы) ---
        lines.append("\n" * 2)
        lines.append("=" * 40)
        lines.append("СПРАВОЧНИК СТАТУСОВ")
        lines.append("=" * 40)

        lines.append("\n--- Внутренние статусы (наша система) ---")
        for code, desc in self.INTERNAL_STATUSES:
            lines.append(f"{code:<22} - {desc}")

        lines.append("\n--- Статусы маркетплейса (Ozon) ---")
        for code, desc in self.OZON_STATUSES:
            lines.append(f"{code:<22} - {desc}")

        return "\n".join(lines)

    # ==================== HTML ====================

    def build_body_html(self) -> str:
        if not self.changes:
            return """
            <html>
            <body style="font-family:Arial, sans-serif; font-size:14px;">
                <p>Добрый день!</p>
                <p>Изменений статусов за этот период не зафиксировано.</p>
            </body>
            </html>
            """

        sorted_changes = sorted(self.changes, key=lambda x: x["new_status"])
        has_cancelled = any(c["new_status"] == "cancelled" for c in sorted_changes)

        # --- основной заголовок и предупреждение ---
        warning = ""
        if has_cancelled:
            warning = """
            <p style="color:#b00020;font-weight:bold;">
                ⚠ ОБНАРУЖЕНЫ ОТМЕНЕННЫЕ ЗАКАЗЫ
            </p>
            """

        # --- строим HTML-таблицу для заказов ---
        rows = []
        for c in sorted_changes:
            # можно подсветить cancelled красным
            color = "color:#b00020;" if c["new_status"] == "cancelled" else ""
            rows.append(f"""
            <tr style="{color}">
                <td style="border:1px solid #ccc;padding:6px;">{c['posting_number']}</td>
                <td style="border:1px solid #ccc;padding:6px;">{c.get('old_status') or 'NEW'}</td>
                <td style="border:1px solid #ccc;padding:6px;">{c['new_status']}</td>
                <td style="border:1px solid #ccc;padding:6px;">{c.get('internal_status', '---')}</td>
            </tr>
            """)

        table_html = f"""
        <table style="border-collapse:collapse;width:100%;font-size:13px;margin-bottom:20px;">
            <tr style="background:#f0f0f0;">
                <th style="border:1px solid #ccc;padding:6px;text-align:left;">Номер заказа</th>
                <th style="border:1px solid #ccc;padding:6px;text-align:left;">Старый статус OZON</th>
                <th style="border:1px solid #ccc;padding:6px;text-align:left;">Новый статус OZON</th>
                <th style="border:1px solid #ccc;padding:6px;text-align:left;">Внутр. статус</th>
            </tr>
            {''.join(rows)}
        </table>
        """

        # --- финальный HTML ---
        return f"""
        <html>
        <body style="font-family:Arial, sans-serif; font-size:14px;">
            <p>Добрый день!</p>
            {warning}
            <p>Зафиксированы изменения статусов заказов на маркетплейсе Ozon:</p>

            {table_html}
            
            <p style="margin-top:30px; margin-bottom:10px;">
                Ниже вы можете ознакомиться с расшифровкой статусов
            </p>
            
            {self._build_status_table(
            'Внутренние статусы (наша система)',
            self.INTERNAL_STATUSES
        )}

            {self._build_status_table(
            'Статусы маркетплейса Ozon',
            self.OZON_STATUSES
        )}
        
            {self.build_signature_html()}
        </body>
        </html>
        """

    # ==================== helpers ====================

    def _build_status_table(self, title: str, rows: list[tuple[str, str]]) -> str:
        trs = "".join(
            f"""
            <tr>
                <td style="border:1px solid #ccc;padding:6px;">
                    <code>{code}</code>
                </td>
                <td style="border:1px solid #ccc;padding:6px;">
                    {desc}
                </td>
            </tr>
            """
            for code, desc in rows
        )

        return f"""
        <h3 style="margin-top:30px;">{title}</h3>
        <table style="
            border-collapse:collapse;
            width:100%;
            font-size:13px;
            margin-bottom:20px;
        ">
            <tr style="background:#f0f0f0;">
                <th style="border:1px solid #ccc;padding:6px;text-align:left;">Статус</th>
                <th style="border:1px solid #ccc;padding:6px;text-align:left;">Описание</th>
            </tr>
            {trs}
        </table>
        """

