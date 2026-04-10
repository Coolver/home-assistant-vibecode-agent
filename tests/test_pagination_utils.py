"""Tests for pagination helpers."""

from app.utils.pagination import filter_items_by_search, paginate_items


def test_paginate_items_defaults_to_first_page():
    result = paginate_items(list(range(300)))
    assert len(result["items"]) == 250
    assert result["page"] == 1
    assert result["page_size"] == 250
    assert result["total"] == 300
    assert result["total_pages"] == 2
    assert result["has_next"] is True
    assert result["next_page"] == 2


def test_paginate_items_out_of_range_page_returns_empty_slice():
    result = paginate_items(list(range(10)), page=5, page_size=3)
    assert result["items"] == []
    assert result["total"] == 10
    assert result["total_pages"] == 4
    assert result["has_next"] is False


def test_paginate_items_full_list_mode():
    result = paginate_items(list(range(3)), page=2, page_size=1, full_list=True)
    assert result["items"] == [0, 1, 2]
    assert result["page"] == 1
    assert result["total_pages"] == 1
    assert result["has_next"] is False


def test_filter_items_by_search():
    items = [
        {"id": "kitchen_lights", "alias": "Kitchen Lights"},
        {"id": "bedroom_heater", "alias": "Bedroom Heater"},
        {"id": "hallway", "alias": "Motion Hallway"},
    ]
    filtered = filter_items_by_search(
        items,
        "kitchen",
        extractors=[lambda item: item.get("id"), lambda item: item.get("alias")],
    )
    assert len(filtered) == 1
    assert filtered[0]["id"] == "kitchen_lights"
