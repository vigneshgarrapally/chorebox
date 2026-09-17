from pathlib import Path

from chorebox.paths import new_files, safe_stem


def test_safe_stem_strips_illegal_chars():
    assert safe_stem('a/b\\c*d?e:f"g<h>i|j') == "abcdefghij"


def test_safe_stem_collapses_whitespace():
    assert safe_stem("  My   Video   Title  ") == "My_Video_Title"


def test_safe_stem_truncates_and_has_fallback():
    assert len(safe_stem("x" * 500)) == 100
    assert safe_stem("   ") == "output"


def test_new_files_only_reports_additions(tmp_path: Path):
    (tmp_path / "clip.mp4").write_text("old")
    before = list(tmp_path.iterdir())
    (tmp_path / "clip.en.vtt").write_text("new")
    (tmp_path / "other.mp4").write_text("unrelated stem")  # must not match

    found = new_files(tmp_path, "clip", before)

    assert found == [tmp_path / "clip.en.vtt"]
