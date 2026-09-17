from pathlib import Path

from chorebox.tools.yt import vtt_to_txt


def test_vtt_to_txt_strips_markup_and_dedupes_scrolling_cues(tmp_path: Path):
    vtt = tmp_path / "clip.en.vtt"
    vtt.write_text(
        "WEBVTT\n"
        "Kind: captions\n"
        "Language: en\n"
        "\n"
        "00:00:00.000 --> 00:00:02.000\n"
        "<c>Hello</c> there\n"
        "\n"
        "00:00:02.000 --> 00:00:04.000\n"
        "Hello there\n"  # auto-captions repeat the previous line while scrolling
        "general kenobi\n"
    )

    out = vtt_to_txt(vtt)

    assert out == vtt.with_suffix(".txt")
    assert not vtt.exists()  # the .vtt is replaced, not left behind
    assert out.read_text() == "Hello there\ngeneral kenobi\n"


def test_vtt_to_txt_drops_cue_numbers_and_blank_lines(tmp_path: Path):
    vtt = tmp_path / "clip.en.vtt"
    vtt.write_text("WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.000\nfirst line\n")

    out = vtt_to_txt(vtt)

    assert out.read_text() == "first line\n"
