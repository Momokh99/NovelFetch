"""Pure-logic tests for the Update/History UI grouping helpers (no Kivy window)."""

from datetime import datetime, timedelta

from gui.screens.history import HistoryTab
from gui.screens.update import UpdateTab


def _midnight_ts(days_ago):
    d = datetime.now() - timedelta(days=days_ago)
    d = d.replace(hour=12, minute=0, second=0, microsecond=0)
    return d.timestamp()


def test_update_group_rows_by_day_ordered():
    t = UpdateTab.__new__(UpdateTab)
    results = [
        {"slug": "a", "updated_ts": _midnight_ts(0)},
        {"slug": "b", "updated_ts": _midnight_ts(1)},
        {"slug": "c"},  # no timestamp
    ]
    groups = t._bucket(results)
    # newest bucket first; untimestamped lands in "Older" last
    labels = [b for b, _ in groups]
    assert labels[0] == "Today"
    assert labels[-1] == "Older"
    assert groups[-1][1][0]["slug"] == "c"
    # today's bucket contains the today-timestamped slug
    today_slugs = {r["slug"] for header, rows in groups if header == "Today"
                   for r in rows}
    assert "a" in today_slugs


def test_update_day_label_today():
    t = UpdateTab.__new__(UpdateTab)
    results = [{"slug": "a", "updated_ts": _midnight_ts(0)}]
    groups = t._bucket(results)
    assert groups == [("Today", results)]


def test_update_group_rows_empty_groups_handled():
    t = UpdateTab.__new__(UpdateTab)
    assert t._bucket([]) == []


def test_history_bucket_ordering_and_members():
    history = [
        {"slug": "old", "last_time": _midnight_ts(30)},
        {"slug": "yesterday", "last_time": _midnight_ts(1)},
        {"slug": "today", "last_time": _midnight_ts(0)},
        {"slug": "week", "last_time": _midnight_ts(3)},
    ]
    buckets = HistoryTab._bucket(history)
    labels = [b for b, _ in buckets]
    assert labels == ["Today", "Yesterday", "This week", "Older"]
    by_slug = {r["slug"] for _, rows in buckets for r in rows}
    assert by_slug == {"old", "yesterday", "today", "week"}


def test_history_bucket_empty():
    assert HistoryTab._bucket([]) == []
