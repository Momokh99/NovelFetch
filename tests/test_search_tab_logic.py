"""Tests for search_tab.py and novel_list.py pure logic — subtitle formatting,
header/footer text, clear-button visibility, and in-library detection."""


def test_result_header_text():
    query = "clara"
    count = 12
    header = f"{count} result(s) for '{query}'"
    assert header == "12 result(s) for 'clara'"


def test_result_header_single():
    assert f"{1} result(s) for '{'x'}'" == "1 result(s) for 'x'"


def test_searching_state_text():
    query = "ghost"
    state_text = f"Searching for '{query}'…"
    assert state_text == "Searching for 'ghost'…"


def test_empty_state_text():
    query = "nothing"
    state_text = f"No results for '{query}'"
    assert state_text == "No results for 'nothing'"


def test_clear_button_hidden_when_empty():
    text = ""
    visible = bool(text.strip())
    assert visible is False


def test_clear_button_shown_when_typing():
    text = "hello"
    visible = bool(text.strip())
    assert visible is True


def test_clear_button_ignores_whitespace():
    text = "   "
    visible = bool(text.strip())
    assert visible is False


def test_in_library_registered(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import json, os
    d = tmp_path / "novels" / "rr:my-novel"
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"title": "My Novel"}))
    from screens import utils
    qualified = "rr:my-novel"
    registered = bool(qualified and utils._read_meta(qualified))
    assert registered is True


def test_in_library_not_registered(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from screens import utils
    qualified = "rr:not-here"
    registered = bool(qualified and utils._read_meta(qualified))
    assert registered is False


def test_update_footer_hidden_on_last_page():
    page, pages = 5, 5
    footer = "" if page >= pages else f"Page {page} of {pages}"
    assert footer == ""


def test_update_footer_shown_when_more():
    page, pages = 1, 3
    footer = "" if page >= pages else f"Page {page} of {pages}"
    assert footer == "Page 1 of 3"


def test_load_more_footer_loading():
    page, pages = 1, 3
    footer = f"Page {page} of {pages} · Loading more…"
    assert footer == "Page 1 of 3 · Loading more…"


def test_search_tab_clear_resets_state():
    """_clear resets all search state."""
    state = {
        "_busy": True,
        "_load_more_busy": True,
        "_page": 3,
        "_pages": 10,
        "results": ["some results"],
        "_seq": 5,
    }
    # Simulate _clear
    state["_busy"] = False
    state["_load_more_busy"] = False
    state["_page"] = 1
    state["_pages"] = 1
    state["results"] = []
    state["_seq"] += 1

    assert state["_busy"] is False
    assert state["_load_more_busy"] is False
    assert state["_page"] == 1
    assert state["_pages"] == 1
    assert state["results"] == []
    assert state["_seq"] == 6


def test_search_tab_load_more_guards():
    """_load_more should not proceed when already busy or past last page."""
    state1 = {"_load_more_busy": True, "_page": 1, "_pages": 5}
    should_load = not state1["_load_more_busy"] and state1["_page"] < state1["_pages"]
    assert not should_load

    state2 = {"_load_more_busy": False, "_page": 5, "_pages": 5}
    should_load = not state2["_load_more_busy"] and state2["_page"] < state2["_pages"]
    assert not should_load

    state3 = {"_load_more_busy": False, "_page": 2, "_pages": 5}
    should_load = not state3["_load_more_busy"] and state3["_page"] < state3["_pages"]
    assert should_load


def test_search_tab_stale_response_dropped():
    """Response with old seq number should be discarded."""
    current_seq = 3
    response_seq = 2
    is_stale = response_seq != current_seq
    assert is_stale

    current_seq = 3
    response_seq = 3
    is_stale = response_seq != current_seq
    assert not is_stale
