from typing import List, Dict
from Common.base_mailer import BaseMailer


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
        ("cancelled", "Заказ отменен клиентом через ЛК ОЗОН"),
    ]

    OZON_STATUSES = [
        ("NOT_VERIFIED", "Заказ создан и ещё не проходил проверку"),
        ("awaiting_packaging", "Ожидает упаковки"),
        ("awaiting_deliver", "Ожидает отгрузки"),
        ("delivering", "Доставляется"),
        ("driver_pickup", "Передан водителю для доставки"),
        ("cancelled", "Заказ отменён"),
        ("delivered", "Заказ доставлен"),
        ("not_accepted", "Не принят на сортировочном центре"),
        ("awaiting_registration", "Ожидает регистрации"),
        ("awaiting_approve", "Ожидает подтверждения"),
        ("client_arbitration", "Клиентский арбитраж доставки"),
        ("arbitration", "Арбитраж"),
        ("acceptance_in_progress", "Идёт приёмка"),
    ]

    # ----------------------------------------------------

    def __init__(self, changes: List[Dict[str, str]], discrepancies: List[Dict[str, str]] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.changes = changes
        self.discrepancies = discrepancies or []

    def has_cancelled_orders(self) -> bool:
        return any(c["new_status"] == "cancelled" for c in self.changes)

    def build_subject_core(self) -> str:
        has_cancelled = any(c["new_status"] == "cancelled" for c in self.changes)
        has_discrepancy = len(self.discrepancies) > 0

        prefix = ""
        if has_cancelled:
            prefix += "⚠ ОБНАРУЖЕНЫ ОТМЕНЕННЫЕ ЗАКАЗЫ | "
        if has_discrepancy:
            prefix += "⚠ ТРЕБУЕТСЯ ВНИМАНИЕ (РАССИНХРОН) | "

        count = len(self.changes) + len(self.discrepancies)
        return f"{prefix}Изменение статусов заказов ({count} шт.)"

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
            f"{'Старый внутр.':<20} | "
            f"{'Новый внутр.':<20}"
        )
        lines.append("-" * 125)

        for c in sorted_changes:
            lines.append(
                f"{c['posting_number']:<25} | "
                f"{str(c.get('old_status') or 'NEW').upper():<25} | "
                f"{str(c['new_status']).upper():<25} | "
                f"{str(c.get('old_internal_status', '---')).upper():<20} | "
                f"{str(c.get('new_internal_status', '---')).upper():<20}"
            )

        # --- блок рассинхронов ---
        if self.discrepancies:
            lines.append("\n" + "!" * 80)
            lines.append("!!! ВНИМАНИЕ: ОБНАРУЖЕН РАССИНХРОН СТАТУСОВ (ТРЕБУЕТСЯ РУЧНАЯ ПРОВЕРКА) !!!")
            lines.append("!" * 80)
            lines.append(f"{'Номер заказа':<25} | {'Внутренний статус':<25} | {'Статус OZON':<25}")
            lines.append("-" * 80)
            for d in self.discrepancies:
                lines.append(
                    f"{d['posting_number']:<25} | "
                    f"{str(d['internal_status']).upper():<25} | "
                    f"{str(d['marketplace_status']).upper():<25}"
                )

        # --- справочник статусов (через константы) ---
        lines.append("\n" * 2)
        lines.append("=" * 40)
        lines.append("СПРАВОЧНИК СТАТУСОВ")
        lines.append("=" * 40)

        lines.append("\n--- Внутренние статусы (наша система) ---")
        for code, desc in self.INTERNAL_STATUSES:
            lines.append(f"{code.upper():<22} - {desc}")

        lines.append("\n--- Статусы маркетплейса (Ozon) ---")
        for code, desc in self.OZON_STATUSES:
            lines.append(f"{code.upper():<22} - {desc}")

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
            warning += """
            <p style="color:#b00020;font-weight:bold;font-size:16px;">
                ⚠ ОБНАРУЖЕНЫ ОТМЕНЕННЫЕ ЗАКАЗЫ
            </p>
            """
        
        if self.discrepancies:
            rows_disc = []
            for d in self.discrepancies:
                rows_disc.append(f"""
                <tr>
                    <td style="border:1px solid #ccc;padding:6px;"><b>{d['posting_number']}</b></td>
                    <td style="border:1px solid #ccc;padding:6px;color:#cc0000;text-align:center;">{str(d['internal_status']).upper()}</td>
                    <td style="border:1px solid #ccc;padding:6px;text-align:center;">{str(d['marketplace_status']).upper()}</td>
                </tr>
                """)
                
            warning += f"""
            <div style="background-color: #fff3f3; border: 2px solid #cc0000; padding: 15px; border-radius: 5px; margin-bottom: 25px;">
                <h3 style="color: #cc0000; margin-top: 0; font-size:18px;">⚠ ТРЕБУЕТСЯ РУЧНАЯ ПРОВЕРКА (РАССИНХРОН)</h3>
                <p>Обнаружены заказы, которые уже отгружены на Ozon, но имеют начальный статус в нашей системе. 
                Они не попадут в реестры склада автоматически.</p>
                <table style="border-collapse:collapse;width:100%;font-size:13px;background:white;">
                    <tr style="background:#f0f0f0;">
                        <th style="border:1px solid #ccc;padding:6px;">Номер заказа</th>
                        <th style="border:1px solid #ccc;padding:6px;">Внутренний статус</th>
                        <th style="border:1px solid #ccc;padding:6px;">Статус на Ozon</th>
                    </tr>
                    {''.join(rows_disc)}
                </table>
            </div>
            """

        # --- строим HTML-таблицу для заказов ---
        rows = []
        for c in sorted_changes:
            # можно подсветить cancelled красным
            color = "color:#b00020;" if c["new_status"] == "cancelled" else ""
            rows.append(f"""
            <tr style="{color}">
                <td style="border:1px solid #ccc;padding:6px;vertical-align:middle;">{c['posting_number']}</td>
                <td style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">{str(c.get('old_status') or 'NEW').upper()}</td>
                <td style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">{str(c['new_status']).upper()}</td>
                <td style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">{str(c.get('old_internal_status', '---')).upper()}</td>
                <td style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">{str(c.get('new_internal_status', '---')).upper()}</td>
            </tr>
            """)

        table_html = f"""
        <table style="border-collapse:collapse;width:100%;font-size:13px;margin-bottom:20px;">
            <tr style="background:#f0f0f0;">
                <th style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">Номер заказа</th>
                <th style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">Старый статус OZON</th>
                <th style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">Новый статус OZON</th>
                <th style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">Старый внутр. статус</th>
                <th style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">Новый внутр. статус</th>
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
                <td style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">
                    <code>{code.upper()}</code>
                </td>
                <td style="border:1px solid #ccc;padding:6px;vertical-align:middle;">
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
                <th style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">Статус</th>
                <th style="border:1px solid #ccc;padding:6px;text-align:center;vertical-align:middle;">Описание</th>
            </tr>
            {trs}
        </table>
        """

