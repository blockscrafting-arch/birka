"""Order status flow: allowed statuses and transitions for manual updates."""

ORDER_STATUSES = (
    "На приемке",
    "Принято",
    "Упаковка",
    "Готово к отгрузке",
    "Завершено",
)

# Допустимые переходы для ручного PATCH (warehouse/admin): из текущего статуса в новый.
# Пустой список для статуса = запрет ручного перехода в этот статус (только через workflow).
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "На приемке": ("Принято",),
    "Принято": ("Упаковка", "На приемке"),
    "Упаковка": ("Готово к отгрузке", "Принято"),
    "Готово к отгрузке": ("Завершено", "Упаковка"),
    "Завершено": ("Готово к отгрузке",),
}


def is_valid_order_status(status: str) -> bool:
    """Проверить, что строка — допустимый статус заявки."""
    return status in ORDER_STATUSES


def is_allowed_transition(current_status: str, new_status: str) -> bool:
    """Проверить, разрешён ли ручной переход из current_status в new_status."""
    if new_status not in ORDER_STATUSES:
        return False
    allowed = ALLOWED_TRANSITIONS.get(current_status, ())
    return new_status in allowed
