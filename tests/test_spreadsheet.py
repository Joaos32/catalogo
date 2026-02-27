import pytest

from catalog.spreadsheet import _extract_sheet_id


def test_extract_sheet_id():
    url = "https://docs.google.com/spreadsheets/d/ABC123xyz/edit?usp=sharing"
    assert _extract_sheet_id(url) == "ABC123xyz"


def test_extract_sheet_id_invalid():
    with pytest.raises(ValueError):
        _extract_sheet_id("https://example.com/not-a-sheet")
