from __future__ import annotations

from .operation_catalog import catalog_entries

_DESTRUCTIVE_EXACT = {
    entry["operation"]
    for entry in catalog_entries()
    if bool(entry.get("destructive"))
}

_DESTRUCTIVE_SHORT = {item.split(".", 1)[1] for item in _DESTRUCTIVE_EXACT if "." in item}

_FALLBACK_HINTS = {
    "move_to_trash",
    "move_items_to_trash",
    "set_items_timestamp",
    "set_timestamp",
    "set_archive",
    "set_favorite",
    "remove_items",
    "delete_item_geo_data",
    "move_to_locked_folder",
    "remove_from_locked_folder",
}


def is_operation_destructive(operation: str) -> bool:
    normalized = operation.strip()
    if normalized in _DESTRUCTIVE_EXACT:
        return True
    short = normalized.split(".", 1)[1] if "." in normalized else normalized
    if short in _DESTRUCTIVE_SHORT:
        return True

    short_lower = short.lower()
    return any(hint in short_lower for hint in _FALLBACK_HINTS)
