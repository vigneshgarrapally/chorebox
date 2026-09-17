from chorebox.timeutil import hms_to_seconds, seconds_to_hms


def test_seconds_to_hms_basic():
    assert seconds_to_hms(0) == "00:00:00"
    assert seconds_to_hms(65) == "00:01:05"
    assert seconds_to_hms(3661) == "01:01:01"


def test_hms_to_seconds_full():
    assert hms_to_seconds("01:01:01") == 3661
    assert hms_to_seconds("1:01:01") == 3661


def test_hms_to_seconds_mm_ss():
    assert hms_to_seconds("01:05") == 65
    assert hms_to_seconds("00:00") == 0


def test_hms_to_seconds_bare_digits():
    assert hms_to_seconds("42") == 42
    assert hms_to_seconds("0") == 0


def test_hms_to_seconds_rejects_garbage():
    assert hms_to_seconds("banana") is None
    assert hms_to_seconds("12:99") is None  # seconds out of range
    assert hms_to_seconds("12:99:00") is None  # minutes out of range
    assert hms_to_seconds("") is None


def test_round_trip():
    for seconds in (0, 1, 59, 60, 3599, 3600, 86399):
        assert hms_to_seconds(seconds_to_hms(seconds)) == seconds
