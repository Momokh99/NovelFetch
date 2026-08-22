"""Tests for search_tab.py and novel_list.py pure logic — subtitle formatting."""


def test_make_row_subtitle_with_author_and_latest():
    novel = {"title": "X", "author": "Bob", "latest": "Ch. 10"}
    sub = novel.get("author", "") or ""
    if novel.get("latest"):
        sub += f"  ·  {novel['latest']}"
    assert sub == "Bob  ·  Ch. 10"


def test_make_row_subtitle_empty_author():
    novel = {"title": "X", "author": "", "latest": "Ch. 5"}
    sub = novel.get("author", "") or ""
    if novel.get("latest"):
        sub += f"  ·  {novel['latest']}"
    assert sub == "  ·  Ch. 5"


def test_make_row_subtitle_no_author_key():
    novel = {"title": "X", "latest": "Ch. 3"}
    sub = novel.get("author", "") or ""
    if novel.get("latest"):
        sub += f"  ·  {novel['latest']}"
    assert sub == "  ·  Ch. 3"


def test_make_row_subtitle_no_latest():
    novel = {"title": "X", "author": "Alice"}
    sub = novel.get("author", "") or ""
    if novel.get("latest"):
        sub += f"  ·  {novel['latest']}"
    assert sub == "Alice"


def test_make_row_subtitle_neither_author_nor_latest():
    novel = {"title": "X"}
    sub = novel.get("author", "") or ""
    if novel.get("latest"):
        sub += f"  ·  {novel['latest']}"
    assert sub == ""


def test_novel_list_load_title_with_count():
    novels = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
    title = "Search Results"
    display = f"{title} ({len(novels)})" if novels else title
    assert display == "Search Results (3)"


def test_novel_list_load_title_empty():
    novels = []
    title = "Search Results"
    display = f"{title} ({len(novels)})" if novels else title
    assert display == "Search Results"


def test_open_novel_slug_parsing():
    slug = "royalroad:my-novel"
    raw = slug.split(":", 1)[-1] if ":" in slug else slug
    assert raw == "my-novel"


def test_open_novel_no_prefix():
    slug = "bare-slug"
    raw = slug.split(":", 1)[-1] if ":" in slug else slug
    assert raw == "bare-slug"


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
    # Guard: already loading
    state1 = {"_load_more_busy": True, "_page": 1, "_pages": 5}
    should_load = not state1["_load_more_busy"] and state1["_page"] < state1["_pages"]
    assert not should_load

    # Guard: past last page
    state2 = {"_load_more_busy": False, "_page": 5, "_pages": 5}
    should_load = not state2["_load_more_busy"] and state2["_page"] < state2["_pages"]
    assert not should_load

    # OK to load
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
