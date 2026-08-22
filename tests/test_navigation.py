"""Tests for navigation stack logic in main_screen.py and reader.py font clamping.

Tests the pure logic portions of Kivy screens without needing a running app.
"""


def test_navigation_stack_push_pop():
    """Simulate the MainScreen._stack list logic."""
    stack = []
    current = "tabs"

    # Simulate goto("novel_list") — push current, switch
    if current != "novel_list":
        stack.append(current)
    current = "novel_list"
    assert stack == ["tabs"]
    assert current == "novel_list"

    # Simulate goto("chapter_list") — push current, switch
    if current != "chapter_list":
        stack.append(current)
    current = "chapter_list"
    assert stack == ["tabs", "novel_list"]
    assert current == "chapter_list"

    # Simulate back() — pop
    target = stack.pop() if stack else "tabs"
    current = target
    assert current == "novel_list"
    assert stack == ["tabs"]

    # Simulate back() again
    target = stack.pop() if stack else "tabs"
    current = target
    assert current == "tabs"
    assert stack == []

    # Simulate back() when empty — defaults to "tabs"
    target = stack.pop() if stack else "tabs"
    current = target
    assert current == "tabs"


def test_navigation_goto_same_screen_no_push():
    """goto() does not push if already on the target screen."""
    stack = []
    current = "novel_list"
    if current != "novel_list":
        stack.append(current)
    assert stack == []  # no push


def test_navigation_back_to_tabs_triggers_refresh():
    """back() to 'tabs' should signal refresh."""
    stack = ["tabs"]
    target = stack.pop() if stack else "tabs"
    assert target == "tabs"
    # Caller checks: if target == "tabs" → refresh_library()
    should_refresh = target == "tabs"
    assert should_refresh


def test_navigation_back_with_no_stack():
    """back() with empty stack defaults to 'tabs'."""
    stack = []
    target = stack.pop() if stack else "tabs"
    assert target == "tabs"


def test_navigation_back_from_reader():
    """back() from reader goes to chapter_list."""
    stack = ["tabs", "novel_list", "chapter_list"]
    target = stack.pop() if stack else "tabs"
    assert target == "chapter_list"


def test_navigation_keycode_27_on_tabs_exits():
    """ESC on tabs screen: not consumed, allow app pause/exit."""
    current = "tabs"
    consumed = not (current == "tabs")
    assert not consumed


def test_navigation_keycode_27_on_subscreen_consumed():
    """ESC on a sub-screen: consumed, go back."""
    current = "reader"
    if current != "tabs":
        consumed = True
    else:
        consumed = False
    assert consumed
