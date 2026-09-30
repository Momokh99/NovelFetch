"""Pure-logic tests for the Update/History UI grouping helpers (no Kivy window)."""

from datetime import datetime, timedelta

from gui.screens.utils import _bucket_by_timestamp


def _midnight_ts(days_ago):
    d = datetime.now() - timedelta(days=days_ago)
    d = d.replace(hour=12, minute=0, second=0, microsecond=0)
    return d.timestamp()


def _update_bucket(results):
    # same key function gui/screens/update.py uses
    return _bucket_by_timestamp(results, lambda r: r.get("updated_ts", 0))


def _history_bucket(history):
    # same key function gui/screens/history.py uses
    return _bucket_by_timestamp(history, lambda h: h.get("last_time", 0))


def test_update_group_rows_by_day_ordered():
    results = [
        {"slug": "a", "updated_ts": _midnight_ts(0)},
        {"slug": "b", "updated_ts": _midnight_ts(1)},
        {"slug": "c"},  # no timestamp
    ]
    groups = _update_bucket(results)
    # newest bucket first; untimestamped lands in "Older" last
    labels = [b for b, _ in groups]
    assert labels[0] == "Today"
    assert labels[-1] == "Older"
    assert groups[-1][1][0]["slug"] == "c"
    # today's bucket contains the today-timestamped slug
    today_slugs = {
        r["slug"] for header, rows in groups if header == "Today" for r in rows
    }
    assert "a" in today_slugs


def test_update_day_label_today():
    results = [{"slug": "a", "updated_ts": _midnight_ts(0)}]
    groups = _update_bucket(results)
    assert groups == [("Today", results)]


def test_update_group_rows_empty_groups_handled():
    assert _update_bucket([]) == []


def test_history_bucket_ordering_and_members():
    today0 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today0 - timedelta(days=today0.weekday())
    history = [
        {"slug": "old", "last_time": _midnight_ts(30)},
        {"slug": "yesterday", "last_time": _midnight_ts(1)},
        {"slug": "today", "last_time": _midnight_ts(0)},
    ]
    expected = ["Today", "Yesterday", "Older"]
    # A day that lands strictly between week_start and yesterday only exists
    # on Wed–Sun; on Mon/Tue the calendar week has no such day, so the
    # "This week" sample is added only when it is actually representable.
    in_week_day = today0 - timedelta(days=2)
    if in_week_day >= week_start:
        history.insert(
            2,
            {
                "slug": "week",
                "last_time": in_week_day.timestamp() + 12 * 3600,
            },
        )
        expected = ["Today", "Yesterday", "This week", "Older"]

    buckets = _history_bucket(history)
    labels = [b for b, _ in buckets]
    assert labels == expected
    by_slug = {r["slug"] for _, rows in buckets for r in rows}
    assert by_slug == {h["slug"] for h in history}


def test_history_bucket_empty():
    assert _history_bucket([]) == []
