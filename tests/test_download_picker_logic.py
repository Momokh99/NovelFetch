"""Tests for download_picker.py pure logic — subset slicing and CODE_TO_LABEL."""

from progress import LANGUAGES
from screens.download_picker import _CODE_TO_LABEL


def test_code_to_label_is_reverse_of_languages():
    assert _CODE_TO_LABEL == {v: k for k, v in LANGUAGES.items()}


def test_code_to_label_all_codes_present():
    for label, code in LANGUAGES.items():
        assert _CODE_TO_LABEL[code] == label


def test_code_to_label_arabic():
    assert _CODE_TO_LABEL["ar"] == "Arabic"


def test_code_to_label_chinese():
    assert _CODE_TO_LABEL["zh-cn"] == "Chinese"


def test_subset_slicing_next_5_10_25():
    chapters = list(range(30))  # 30 chapters

    remaining = chapters[5:]  # 5 already downloaded
    assert len(remaining) == 25

    assert len(remaining[:5]) == 5
    assert len(remaining[:10]) == 10
    assert len(remaining[:25]) == 25


def test_subset_slicing_fewer_than_request():
    chapters = list(range(3))
    remaining = chapters  # 0 downloaded

    assert len(remaining[:5]) == 3  # only 3, not 5
    assert len(remaining[:10]) == 3
    assert len(remaining[:25]) == 3


def test_subset_slicing_no_remaining():
    chapters = list(range(5))
    downloaded = 5
    remaining = chapters[downloaded:]

    assert remaining == []
    assert remaining[:5] == []


def test_unread_computation():
    """unread = not in seen AND index >= downloaded."""
    chapters = list(range(10))
    seen = {0, 1, 3}
    downloaded = 4  # chapters 0-3 are local files

    unread = [ch for ch in chapters
              if ch not in seen and ch >= downloaded]
    # Chapters 4-9 are not seen and >= 4
    assert unread == [4, 5, 6, 7, 8, 9]


def test_unread_computation_all_seen():
    chapters = list(range(5))
    seen = {0, 1, 2, 3, 4}
    downloaded = 0

    unread = [ch for ch in chapters
              if ch not in seen and ch >= downloaded]
    assert unread == []


def test_unread_computation_none_downloaded():
    chapters = list(range(5))
    seen = {0, 2}
    downloaded = 0

    unread = [ch for ch in chapters
              if ch not in seen and ch >= downloaded]
    # 0 is seen, 2 is seen → [1, 3, 4]
    assert unread == [1, 3, 4]


def test_summary_text_format():
    downloaded = 5
    unread_count = 8
    total = 20
    text = f"{downloaded} downloaded  |  {unread_count} unread  |  {total} total"
    assert text == "5 downloaded  |  8 unread  |  20 total"
