"""Database query helpers (e.g. safe ILIKE escaping)."""


def escape_ilike(value: str) -> str:
    """Escape % and _ for safe use in SQL ILIKE (use with escape='\\\\')."""
    if not value:
        return value
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
