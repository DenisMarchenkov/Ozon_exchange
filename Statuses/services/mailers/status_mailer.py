from typing import List, Dict
from Common.base_mailer import BaseMailer

class StatusMailer(BaseMailer):
    """
    Письмо об изменении статусов заказов на маркетплейсе.
    """

    def __init__(self, changes: List[Dict[str, str]], *args, **kwargs):
        """
        :param changes: список словарей вида {"posting_number": str, "old_status": str, "new_status": str}
        :param args, kwargs: передаются в BaseMailer
        """
        super().__init__(*args, **kwargs)
        self.changes = changes

    def build_subject_core(self) -> str:
        return f"Изменение статусов заказов ({len(self.changes)} шт.)"

    def build_body(self) -> str:
        if not self.changes:
            return "Добрый день!\n\nИзменений статусов за этот период не зафиксировано.\n"

        # Сортировка по новому статусу
        sorted_changes = sorted(self.changes, key=lambda x: x['new_status'])

        has_cancelled = any(c['new_status'] == 'cancelled' for c in sorted_changes)

        body_lines = ["Добрый день!\n"]

        if has_cancelled:
            body_lines.append("!!! ВНИМАНИЕ: ОБНАРУЖЕНЫ ОТМЕНЕННЫЕ ЗАКАЗЫ !!!")
            body_lines.append("Пожалуйста, проверьте список ниже и примите меры.\n")

        body_lines.append("Зафиксированы изменения статусов заказов на маркетплейсе Ozon:\n")
        body_lines.append(f"{'Номер заказа':<25} | {'Старый статус':<25} | {'Новый статус':<25} | {'Внутр. статус':<20}")
        body_lines.append("-" * 105)

        for change in sorted_changes:
            old_st = change['old_status'] or 'NEW'
            new_st = change['new_status']
            int_st = change.get('internal_status', '---')
            line = f"{change['posting_number']:<25} | {old_st:<25} | {new_st:<25} | {int_st:<20}"
            body_lines.append(line)

        # Добавляем справку по статусам
        body_lines.append("\n" + "="*40)
        body_lines.append("СПРАВОЧНИК СТАТУСОВ")
        body_lines.append("="*40)
        
        body_lines.append("\n--- Внутренние статусы (наша система) ---")
        body_lines.append("NEW                    - Заказ только что импортирован из файла")
        body_lines.append("confirmed              - Подтвержден офисом, готов к передаче в Ozon")
        body_lines.append("awaiting_confirmation  - Есть отказы по позициям, нужно подтверждение офиса")
        body_lines.append("ship_not_available     - Ozon временно отклонил сборку заказа")
        body_lines.append("is_gtd_absent          - Не заполнены номера ГТД")
        body_lines.append("is_marking_absent      - Не заполнены коды маркировки (Честный Знак)")
        body_lines.append("awaiting_delivery      - Заказ успешно передан в сборку на стороне Ozon")
        body_lines.append("error                  - Ошибка при попытке собрать заказ через API")
        body_lines.append("IN_DISPATCH            - Заказ включен в задание для склада")

        body_lines.append("\n--- Статусы маркетплейса (Ozon) ---")
        body_lines.append("awaiting_packaging     - ожидает упаковки")
        body_lines.append("awaiting_deliver       - ожидает отгрузки (собран)")
        body_lines.append("delivering             - доставляется")
        body_lines.append("driver_pickup          - у водителя")
        body_lines.append("cancelled              - отменено")
        body_lines.append("delivered              - доставлен")
        body_lines.append("not_accepted           - не принят на сортировочном центре")
        body_lines.append("awaiting_registration  - ожидает регистрации")
        body_lines.append("awaiting_approve       - ожидает подтверждения")
        body_lines.append("client_arbitration     - клиентский арбитраж доставки")
        body_lines.append("arbitration            - арбитраж")
        body_lines.append("acceptance_in_progress - идёт приёмка")

        return "\n".join(body_lines)
