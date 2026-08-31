"""Tests for screens/history.py _time_ago (pure logic, no Kivy UI)."""

import time
from datetime import datetime

from gui.screens.history import _time_ago


def test_time_ago_none_returns_empty():
    assert _time_ago(None) == ""


def test_time_ago_zero_returns_empty():
    assert _time_ago(0) == ""


def test_time_ago_just_now():
    now = datetime.now().timestamp()
    assert _time_ago(now - 30) == "just now"
    assert _time_ago(now - 59) == "just now"


def test_time_ago_minutes():
    now = datetime.now().timestamp()
    assert _time_ago(now - 60) == "1m ago"
    assert _time_ago(now - 900) == "15m ago"
    assert _time_ago(now - 3540) == "59m ago"


def test_time_ago_hours():
    now = datetime.now().timestamp()
    assert _time_ago(now - 3600) == "1h ago"
    assert _time_ago(now - 7200) == "2h ago"
    assert _time_ago(now - 82800) == "23h ago"


def test_time_ago_days():
    now = datetime.now().timestamp()
    assert _time_ago(now - 86400) == "1d ago"
    assert _time_ago(now - 172800) == "2d ago"
    assert _time_ago(now - 518400) == "6d ago"


def test_time_ago_weeks():
    now = datetime.now().timestamp()
    assert _time_ago(now - 604800) == "1w ago"
    assert _time_ago(now - 1209600) == "2w ago"
    assert _time_ago(now - 2592000) == "4w ago"


def test_time_ago_boundary_60s():
    now = datetime.now().timestamp()
    # Exactly at 60s = 1 minute
    assert _time_ago(now - 60) == "1m ago"
    # Just under 60s = just now
    assert _time_ago(now - 59) == "just now"


def test_time_ago_boundary_60min():
    now = datetime.now().timestamp()
    assert _time_ago(now - 3600) == "1h ago"
    assert _time_ago(now - 3599) == "59m ago"


def test_time_ago_boundary_24h():
    now = datetime.now().timestamp()
    assert _time_ago(now - 86400) == "1d ago"
    assert _time_ago(now - 86399) == "23h ago"


def test_time_ago_boundary_7d():
    now = datetime.now().timestamp()
    assert _time_ago(now - 604800) == "1w ago"
    assert _time_ago(now - 604799) == "6d ago"
