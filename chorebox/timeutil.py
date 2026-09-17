"""HH:MM:SS <-> seconds, shared by any tool that deals in time ranges."""

from datetime import timedelta


def seconds_to_hms(seconds: float) -> str:
    total = int(timedelta(seconds=int(seconds)).total_seconds())
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{secs:02}"


def hms_to_seconds(value: str) -> int | None:
    """Parse HH:MM:SS, H:MM:SS, MM:SS or a bare seconds count."""
    import re

    text = value.strip()
    if text.isdigit():
        return int(text)
    match = re.match(r"(?:(\d+):)?(\d{1,2}):(\d{1,2})$", text)
    if not match:
        return None
    hours, minutes, secs = match.groups()
    minutes, secs = int(minutes), int(secs)
    if not (0 <= minutes < 60 and 0 <= secs < 60):
        return None
    return (int(hours) if hours else 0) * 3600 + minutes * 60 + secs
