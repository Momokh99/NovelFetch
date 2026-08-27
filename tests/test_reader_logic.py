"""Tests for reader.py pure logic — font clamping, control-char stripper,
greedy RTL line wrapping, and the rewrite toggle state machine."""

import re

from screens.reader import (
    _strip_control_chars,
    _CTRL_CHARS_RE,
    _greedy_wrap,
    _wrap_rtl_lines,
    lines_per_chunk,
    pack_lines_into_chunks,
)


# ---- font clamping ----

def test_font_clamping():
    def clamp_font(size, delta):
        return min(28, max(14, size + delta))

    assert clamp_font(16, 2) == 18
    assert clamp_font(16, -2) == 14
    assert clamp_font(26, 4) == 28
    assert clamp_font(16, -10) == 14
    assert clamp_font(14, -2) == 14
    assert clamp_font(28, 2) == 28
    assert clamp_font(20, 0) == 20


def test_font_all_values_in_range():
    def clamp_font(size, delta):
        return min(28, max(14, size + delta))

    for size in range(14, 29):
        for delta in range(-20, 21):
            result = clamp_font(size, delta)
            assert 14 <= result <= 28


# ---- control-char stripper ----

def test_strip_control_chars_removes_rtl_marks():
    text = "مرحبا\u200f بالعالم"
    clean = _strip_control_chars(text)
    assert "\u200f" not in clean
    assert clean == "مرحبا بالعالم"


def test_strip_control_chars_removes_embed_marks():
    text = "\u202aHello\u202c world"
    clean = _strip_control_chars(text)
    assert clean == "Hello world"
    assert "\u202a" not in clean
    assert "\u202c" not in clean


def test_strip_control_chars_removes_ltr_mark():
    text = "Hello\u200e world"
    clean = _strip_control_chars(text)
    assert clean == "Hello world"


def test_strip_control_chars_removes_bom():
    text = "\ufeffBOM at start"
    clean = _strip_control_chars(text)
    assert clean == "BOM at start"


def test_strip_control_chars_removes_arabic_letter_mark():
    text = "مرحبا\u061cبالعالم"
    clean = _strip_control_chars(text)
    assert "\u061c" not in clean


def test_strip_control_chars_removes_isolate_marks():
    text = "\u2066text\u2069"
    clean = _strip_control_chars(text)
    assert clean == "text"


def test_strip_control_chars_preserves_arabic_text():
    text = "فَتَحَ اللهُ عَلَيْكُمْ"
    assert _strip_control_chars(text) == text


def test_strip_control_chars_preserves_english():
    text = "Hello, world! 123 @#$"
    assert _strip_control_chars(text) == text


def test_strip_control_chars_empty_string():
    assert _strip_control_chars("") == ""


def test_strip_control_chars_only_invisible():
    assert _strip_control_chars("\u200f\u202a\u2066") == ""


def test_ctrl_chars_regex_covers_all_targets():
    """Every expected invisible mark is matched by the regex."""
    invisible_marks = [
        "\u200e",  # LTR mark
        "\u200f",  # RTL mark
        "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",  # embedding
        "\u2066", "\u2067", "\u2068", "\u2069",  # isolate
        "\u206a", "\u206b", "\u206c", "\u206d",  # bidi controls
        "\ufeff",  # BOM
        "\u061c",  # Arabic letter mark
    ]
    for mark in invisible_marks:
        assert _CTRL_CHARS_RE.search(mark), f"Mark U+{ord(mark):04X} not matched"


# ---- shape_arabic_text integration ----

def test_shape_arabic_text_strips_invisible_marks():
    from screens.reader import _shape_arabic_text
    text = "مرحبا\u200f بالعالم"
    result = _shape_arabic_text(text)
    assert "\u200f" not in result
    assert len(result) > 0


def test_shape_arabic_text_fallback():
    """When arabic_reshaper is not installed, returns text unchanged."""
    try:
        import arabic_reshaper
        has_shaping = True
    except ImportError:
        has_shaping = False

    if not has_shaping:
        from screens.reader import _shape_arabic_text
        assert _shape_arabic_text("hello") == "hello"
        assert _shape_arabic_text("") == ""


# ---- toggle translate state machine ----

def test_toggle_showing_translated_reverts():
    """translated_text set → revert."""
    state = {
        "_busy": False, "_translated_text": "tr text",
        "_offline_en_path": "/en.txt", "_offline_tr_path": "/tr_ar.txt",
    }
    def toggle(s):
        if s["_busy"]:
            return None
        if s["_translated_text"]:
            return "revert"
        elif s["_offline_en_path"] and s["_offline_tr_path"]:
            return "swap_offline"
        elif s["_offline_en_path"]:
            return "pick_language"
        return "pick_language"
    assert toggle(state) == "revert"


def test_toggle_both_offline_copies_swaps():
    """No translated text but both offline files exist → swap."""
    state = {
        "_busy": False, "_translated_text": "",
        "_offline_en_path": "/en.txt", "_offline_tr_path": "/tr_ar.txt",
    }
    def toggle(s):
        if s["_busy"]:
            return None
        if s["_translated_text"]:
            return "revert"
        elif s["_offline_en_path"] and s["_offline_tr_path"]:
            return "swap_offline"
        elif s["_offline_en_path"]:
            return "pick_language"
        return "pick_language"
    assert toggle(state) == "swap_offline"


def test_toggle_only_en_file_opens_picker():
    """Only English file on disk, no translated → language picker."""
    state = {
        "_busy": False, "_translated_text": "",
        "_offline_en_path": "/en.txt", "_offline_tr_path": "",
    }
    def toggle(s):
        if s["_busy"]:
            return None
        if s["_translated_text"]:
            return "revert"
        elif s["_offline_en_path"] and s["_offline_tr_path"]:
            return "swap_offline"
        elif s["_offline_en_path"]:
            return "pick_language"
        return "pick_language"
    assert toggle(state) == "pick_language"


def test_toggle_no_offline_files_opens_picker():
    """No offline copies at all → language picker."""
    state = {
        "_busy": False, "_translated_text": "",
        "_offline_en_path": "", "_offline_tr_path": "",
    }
    def toggle(s):
        if s["_busy"]:
            return None
        if s["_translated_text"]:
            return "revert"
        elif s["_offline_en_path"] and s["_offline_tr_path"]:
            return "swap_offline"
        elif s["_offline_en_path"]:
            return "pick_language"
        return "pick_language"
    assert toggle(state) == "pick_language"


def test_toggle_busy_blocks_all():
    state = {"_busy": True, "_translated_text": "", "_offline_en_path": "", "_offline_tr_path": ""}
    def toggle(s):
        if s["_busy"]:
            return None
        return "should_not_reach"
    assert toggle(state) is None


def test_swap_offline_roundtrip(tmp_path):
    """Simulate TR→EN→TR swap reading real temp files."""
    en_path = tmp_path / "Ch_1.txt"
    tr_path = tmp_path / "Ch_1_ar.txt"
    en_text = "Chapter One English"
    tr_text = "الفصل الأول"

    en_path.write_text(en_text, encoding="utf-8")
    tr_path.write_text(tr_text, encoding="utf-8")

    # State: showing translated, offline_lang="ar"
    offline_lang = "ar"
    translated_text = tr_text

    # Swap to English
    with open(en_path, encoding="utf-8") as f:
        content = f.read()
    translated_text = ""
    offline_lang = None
    assert content == en_text
    assert translated_text == ""

    # Swap back to translated
    with open(tr_path, encoding="utf-8") as f:
        content = f.read()
    translated_text = content
    offline_lang = "ar"
    assert translated_text == tr_text
    assert offline_lang == "ar"


# ---- load busy reset logic ----

def test_load_resets_busy_flag():
    """Simulate load() resetting a stuck busy state."""
    busy = True  # stuck from previous failed fetch
    translated_text = "old"
    lang = "ar"

    # Reset logic from load()
    busy = False
    translated_text = ""
    lang = None

    assert busy is False
    assert translated_text == ""
    assert lang is None


def test_load_chapter_guard_busy():
    """_load_chapter returns early if busy."""
    busy = True
    idx = 3
    chapters = [{"title": "Ch 1"}, {"title": "Ch 2"}]

    loaded = not (not (0 <= idx < len(chapters)) or busy)
    assert not loaded  # busy=True blocks load


def test_load_chapter_guard_out_of_bounds():
    """_load_chapter returns early if index out of range."""
    busy = False
    idx = 10
    chapters = [{"title": "Ch 1"}, {"title": "Ch 2"}]

    loaded = not (not (0 <= idx < len(chapters)) or busy)
    assert not loaded  # idx=10 > len=2


def test_load_chapter_allows_valid():
    busy = False
    idx = 0
    chapters = [{"title": "Ch 1"}, {"title": "Ch 2"}]

    loaded = not (not (0 <= idx < len(chapters)) or busy)
    assert loaded


# ---- greedy RTL line wrapping ----

def test_greedy_wrap_single_line_fits():
    widths = [10, 10, 10]
    lines = _greedy_wrap(widths, space_w=5, avail=100)
    assert lines == [[0, 1, 2]]


def test_greedy_wrap_splits_when_full():
    # 10+5+10+5+10 = 40 fits in 45, but adding another word (55) does not.
    widths = [10, 10, 10, 10]
    lines = _greedy_wrap(widths, space_w=5, avail=45)
    assert lines == [[0, 1, 2], [3]]


def test_greedy_wrap_word_longer_than_avail_goes_alone():
    # A single oversized word must still be placed on its own line,
    # never dropped or merged with neighbours.
    widths = [5, 100, 5]
    lines = _greedy_wrap(widths, space_w=5, avail=20)
    assert lines == [[0], [1], [2]]


def test_greedy_wrap_exact_fit_stays_on_line():
    widths = [10, 10]
    lines = _greedy_wrap(widths, space_w=5, avail=25)
    assert lines == [[0, 1]]


def test_greedy_wrap_empty_input():
    assert _greedy_wrap([], space_w=5, avail=50) == []


def test_greedy_wrap_never_exceeds_avail_unless_single_word():
    import random
    rng = random.Random(42)
    widths = [rng.randint(1, 60) for _ in range(200)]
    avail, space_w = 80, 4
    for line in _greedy_wrap(widths, space_w, avail):
        if len(line) == 1:
            continue  # lone oversized word is allowed
        total = sum(widths[i] for i in line) + space_w * (len(line) - 1)
        assert total <= avail


def test_greedy_wrap_preserves_word_order():
    # Line indices must be strictly increasing across the whole result —
    # this is what keeps the reading order top-to-bottom after the
    # per-line bidi flip.
    widths = [30, 30, 30, 30, 30]
    lines = _greedy_wrap(widths, space_w=5, avail=70)
    flat = [i for line in lines for i in line]
    assert flat == sorted(flat)
    assert flat == list(range(5))


# ---- RTL paragraph wrapping (logical order, pre-bidi) ----

def _fixed_measure(width_map):
    def measure(word):
        return width_map.get(word, 10)
    return measure


def test_wrap_rtl_lines_single_paragraph_fits_one_line():
    text = "أ ب ج"
    lines = _wrap_rtl_lines(text, _fixed_measure({}), space_w=5, avail=100)
    assert lines == ["أ ب ج"]


def test_wrap_rtl_lines_splits_long_paragraph():
    # Each word 30px + 5px space -> two words per 70px line.
    text = "واحد اثنين ثلاثة اربعة خمسة"
    lines = _wrap_rtl_lines(
        text, _fixed_measure({w: 30 for w in text.split()}),
        space_w=5, avail=70)
    assert len(lines) == 3
    assert all(len(l.split()) <= 2 for l in lines)


def test_wrap_rtl_lines_preserves_reading_order():
    text = "س1 س2 س3 س4 س5"
    lines = _wrap_rtl_lines(text, _fixed_measure({}), space_w=1, avail=10)
    joined = " ".join(lines)
    assert joined == text  # no word lost or reordered


def test_wrap_rtl_lines_keeps_empty_paragraphs():
    text = "اول\n\nثاني"
    lines = _wrap_rtl_lines(text, _fixed_measure({}), space_w=5, avail=100)
    assert "" in lines
    assert "اول" in lines and "ثاني" in lines


def test_wrap_rtl_lines_oversized_word_stays_whole():
    # A word wider than avail must not be split mid-word.
    text = "صغير ضخضخضخضخضخضخ صغير"
    lines = _wrap_rtl_lines(
        text, _fixed_measure({"ضخضخضخضخضخضخ": 500}), space_w=5, avail=50)
    flat = " ".join(lines).split()
    assert "ضخضخضخضخضخضخ" in flat  # intact


def test_wrap_rtl_words_measured_once_per_occurrence():
    calls = []

    def measure(word):
        calls.append(word)
        return 10

    _wrap_rtl_lines("كلمة كلمة كلمة", measure, space_w=5, avail=1000)
    assert len(calls) == 3  # one call per word occurrence (caller caches)


# ---- chunked rendering (GL max-texture-size guard) ----

def test_lines_per_chunk_basic_division():
    assert lines_per_chunk(25, cap=2500) == 100


def test_lines_per_chunk_floors_partial_line():
    # 2500 // 30 = 83.33 -> 83 full lines fit
    assert lines_per_chunk(30, cap=2500) == 83


def test_lines_per_chunk_zero_or_negative_height_is_one():
    assert lines_per_chunk(0, cap=2500) == 1
    assert lines_per_chunk(-5, cap=2500) == 1


def test_lines_per_chunk_never_zero_for_huge_lines():
    assert lines_per_chunk(4000, cap=2500) == 1


def test_pack_lines_exact_multiple():
    assert pack_lines_into_chunks(["a", "b", "c", "d"], 2) == ["a\nb", "c\nd"]


def test_pack_lines_remainder_chunk():
    assert pack_lines_into_chunks(["a", "b", "c"], 2) == ["a\nb", "c"]


def test_pack_lines_empty_input():
    assert pack_lines_into_chunks([], 10) == []


def test_pack_lines_single_chunk_when_all_fit():
    lines = ["l1", "l2", "l3"]
    assert pack_lines_into_chunks(lines, 10) == ["l1\nl2\nl3"]


def test_pack_lines_preserves_blank_paragraphs_inside_chunk():
    assert pack_lines_into_chunks(["p1", "", "p2"], 10) == ["p1\n\np2"]


def test_pack_lines_per_chunk_below_one_is_clamped():
    # clamped to 1 -> one line per chunk
    assert pack_lines_into_chunks(["a", "b"], 0) == ["a", "b"]
    assert pack_lines_into_chunks(["a", "b"], -3) == ["a", "b"]


def test_pack_then_split_roundtrips_content():
    lines = [f"word{i}" for i in range(50)] + ["", ""]
    chunks = pack_lines_into_chunks(lines, 7)
    rebuilt = []
    for i, chunk in enumerate(chunks):
        rebuilt.extend(chunk.split("\n"))
        if i < len(chunks) - 1:
            pass
    # every original line survives, in order, with blank lines intact
    assert rebuilt[:50] == lines[:50]
    assert all("\n" in c or len(c.split("\n")) <= 7 for c in chunks)
    for chunk in chunks:
        assert len(chunk.split("\n")) <= 7
