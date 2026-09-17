"""Local video actions: trim a segment, extract audio. No network involved —
this is the local-file counterpart to `yt trim`/`yt download --quality audio`.
"""

import subprocess
from pathlib import Path

from ..console import console
from ..errors import ChoreboxError
from ..paths import require_ffmpeg, resolve_outdir
from ..registry import Arg, tool
from ..timeutil import hms_to_seconds

VIDEO = tool("video", "Local video")

AUDIO_CODECS = {
    "m4a": "aac",
    "mp3": "libmp3lame",
    "wav": "pcm_s16le",
    "opus": "libopus",
}

FILE = Arg("file", "Video file", kind="path")
OUTDIR = Arg("outdir", "Save to (blank = next to the source file)", flag="-o/--outdir", kind="path")


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(
        [require_ffmpeg(), "-y", *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        last_line = result.stderr.strip().splitlines()[-1] if result.stderr else "ffmpeg failed"
        raise ChoreboxError(last_line)


@VIDEO.action(
    "trim",
    "Trim a local video (fast, stream-copy cut)",
    args=[
        FILE,
        Arg("start", "Start time", flag="-s/--start", default="00:00:00"),
        Arg("end", "End time", flag="-e/--end"),
        Arg("name", "Output filename", flag="-n/--name"),
        OUTDIR,
    ],
)
def trim(
    file: str,
    start: str = "00:00:00",
    end: str | None = None,
    name: str | None = None,
    outdir: str | None = None,
) -> int:
    """Stream-copy trim (`-c copy`) — fast and lossless, but cuts snap to the
    nearest keyframe, so boundaries can land within a second or two of what
    you asked for. A frame-accurate re-encode mode is a documented follow-up
    (see CLAUDE.md) for when that slack matters."""
    src = Path(file).expanduser()
    if not src.is_file():
        raise ChoreboxError(f"No such file: {src}")
    if end is None:
        raise ChoreboxError("An end time is required (-e/--end).")

    start_s, end_s = hms_to_seconds(start), hms_to_seconds(end)
    if start_s is None or end_s is None:
        raise ChoreboxError("Times must look like HH:MM:SS, MM:SS or a plain seconds count.")
    if start_s >= end_s:
        raise ChoreboxError("Start time must come before end time.")

    out = resolve_outdir(outdir) if outdir else src.parent
    dest = out / (name or f"{src.stem}-trim{src.suffix}")
    _run_ffmpeg(["-ss", start, "-to", end, "-i", str(src), "-c", "copy", str(dest)])
    console.print(f"[success]✓ Saved[/success] [url]{dest.resolve()}[/url]", soft_wrap=True)
    return 0


@VIDEO.action(
    "extract-audio",
    "Extract the audio track from a local video",
    args=[
        FILE,
        Arg(
            "fmt",
            "Audio format",
            flag="-f/--format",
            kind="choice",
            choices=tuple(AUDIO_CODECS),
            default="m4a",
        ),
        OUTDIR,
    ],
)
def extract_audio(file: str, fmt: str = "m4a", outdir: str | None = None) -> int:
    src = Path(file).expanduser()
    if not src.is_file():
        raise ChoreboxError(f"No such file: {src}")
    if fmt not in AUDIO_CODECS:
        raise ChoreboxError(f"Unknown format {fmt!r}; pick one of {', '.join(AUDIO_CODECS)}.")

    out = resolve_outdir(outdir) if outdir else src.parent
    dest = out / f"{src.stem}.{fmt}"
    _run_ffmpeg(["-i", str(src), "-vn", "-acodec", AUDIO_CODECS[fmt], str(dest)])
    console.print(f"[success]✓ Saved[/success] [url]{dest.resolve()}[/url]", soft_wrap=True)
    return 0
