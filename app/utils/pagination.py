"""Pagination and lightweight filtering helpers for list endpoints."""

from math import ceil
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE = 250


def _normalize_page_size(page_size: Optional[int]) -> int:
    if page_size is None:
        return DEFAULT_PAGE_SIZE
    return max(1, min(int(page_size), MAX_PAGE_SIZE))


def _coerce_bool(value: Any, default: bool = False) -> bool:
    """Treat only real bools as booleans; FastAPI Query(...) defaults are not bool."""
    return value if isinstance(value, bool) else default


def _coerce_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_optional_int(value: Any, default: Optional[int]) -> Optional[int]:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).lower()


def filter_items_by_search(
    items: Sequence[Any],
    search: Optional[Any],
    extractors: Iterable[Callable[[Any], Any]],
) -> List[Any]:
    """Filter items by case-insensitive substring across extracted values."""
    # When FastAPI route handlers are called directly (e.g. in tests), `Query(...)`
    # defaults are not resolved — `search` may be a Query/ParameterInfo object, not str.
    if not isinstance(search, str):
        return list(items)

    needle = search.strip().lower()
    if not needle:
        return list(items)

    filtered: List[Any] = []
    for item in items:
        for extractor in extractors:
            haystack = _to_text(extractor(item))
            if needle in haystack:
                filtered.append(item)
                break
    return filtered


def paginate_items(
    items: Sequence[Any],
    page: int = 1,
    page_size: Optional[int] = None,
    full_list: bool = False,
) -> Dict[str, Any]:
    """Paginate a list and return slice with metadata."""
    page = _coerce_int(page, 1)
    full_list = _coerce_bool(full_list, False)
    page_size = _coerce_optional_int(page_size, None)
    normalized_page = max(1, int(page))
    normalized_page_size = _normalize_page_size(page_size)
    total = len(items)

    if full_list:
        effective_page_size = total if total > 0 else normalized_page_size
        return {
            "items": list(items),
            "total": total,
            "page": 1,
            "page_size": effective_page_size,
            "total_pages": 1 if total > 0 else 0,
            "has_next": False,
            "next_page": None,
        }

    total_pages = ceil(total / normalized_page_size) if total > 0 else 0
    if total_pages == 0:
        return {
            "items": [],
            "total": 0,
            "page": normalized_page,
            "page_size": normalized_page_size,
            "total_pages": 0,
            "has_next": False,
            "next_page": None,
        }

    if normalized_page > total_pages:
        return {
            "items": [],
            "total": total,
            "page": normalized_page,
            "page_size": normalized_page_size,
            "total_pages": total_pages,
            "has_next": False,
            "next_page": None,
        }

    start = (normalized_page - 1) * normalized_page_size
    end = start + normalized_page_size
    has_next = normalized_page < total_pages
    return {
        "items": list(items[start:end]),
        "total": total,
        "page": normalized_page,
        "page_size": normalized_page_size,
        "total_pages": total_pages,
        "has_next": has_next,
        "next_page": normalized_page + 1 if has_next else None,
    }
