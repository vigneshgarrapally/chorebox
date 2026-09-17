"""YouTube actions: download, subtitles/transcript, trim a segment, metadata.

Ported from this project's dotfiles-era prototype (home/tools/toolbox in
vigneshgarrapally/dotfiles) — that version was hand-verified against a real
video (metadata, a 7s trim measured exact with ffprobe, transcript text,
audio-only download). Logic here is unchanged from that verification.
"""

import re
import shutil
from pathlib import Path

import yt_dlp
from rich.table import Table
from yt_dlp.utils import download_range_func

from ..console import console
from ..errors import ChoreboxError
from ..paths import new_files, require_ffmpeg, resolve_outdir, safe_stem
from ..registry import Arg, tool
from ..timeutil import hms_to_seconds, seconds_to_hms

YT = tool("yt", "YouTube")

QUALITIES = {
    "best": "bv*+ba/b",
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "720p": "bv*[height<=720]+ba/b[height<=720]",
    "audio": "ba/b",
}
SUB_FORMATS = ("txt", "srt", "vtt")

URL = Arg("url", "Video URL")
OUTDIR = Arg("outdir", "Save to", flag="-o/--outdir", kind="path")
QUIET = Arg("quiet", "Quiet — print only the output paths", flag="-q/--quiet", kind="flag")


# --- shared helpers (yt-dlp plumbing, not part of the plugin contract) ---


def _get_js_runtime() -> str | None:
    """The preferred JS runtime for yt-dlp's YouTube extractor, if installed."""
    for runtime in ("deno", "node", "bun"):
        if shutil.which(runtime):
            return runtime
    return None


def _ydl_opts(quiet: bool) -> dict:
    opts: dict = {
        "quiet": quiet,
        "no_warnings": quiet,
        "noprogress": quiet,
        "nocheckcertificate": True,
    }
    runtime = _get_js_runtime()
    if runtime:
        # Lets yt-dlp solve YouTube's JS challenges instead of falling back
        # to its slower/flakier pure-Python path.
        opts["extractor_args"] = {"youtube": {"js_runtimes": [runtime]}}
        opts["remote_components"] = ["ejs:github"]  # a list — a bare string
        # gets iterated character-by-character by yt-dlp and silently warns.
    return opts


def _fetch_info(url: str) -> dict:
    # Always silent: metadata is a means to an end, not output the user asked for.
    with yt_dlp.YoutubeDL(_ydl_opts(quiet=True)) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as exc:
            raise ChoreboxError(f"Could not read that URL: {exc}") from exc
    if info is None:
        raise ChoreboxError("yt-dlp returned no metadata for that URL.")
    if info.get("_type") == "playlist":
        raise ChoreboxError("That URL is a playlist — pass a single video URL.")
    return info


def _print_info(info: dict) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[bold]Title:[/bold]", info.get("title") or "Unknown")
    table.add_row("[bold]Uploader:[/bold]", info.get("uploader") or "Unknown")
    duration = info.get("duration")
    table.add_row(
        "[bold]Duration:[/bold]",
        seconds_to_hms(duration) if duration else "live/unknown",
    )
    console.print(table)


def _report_written(paths, fallback, quiet: bool) -> None:
    written = [p for p in paths if p.exists()]
    if not written:
        written = [fallback] if fallback.exists() else []
    if quiet:
        for path in written:
            print(path.resolve())
        return
    if not written:
        console.print("[warning]Finished, but no output file was found.[/warning]")
        return
    for path in written:
        console.print(f"[success]✓ Saved[/success] [url]{path.resolve()}[/url]", soft_wrap=True)


# --- actions ---


@YT.action("info", "Show metadata only", args=[URL])
def info(url: str) -> int:
    with console.status("[info]Fetching metadata...", spinner="earth"):
        data = _fetch_info(url)
    _print_info(data)
    return 0


@YT.action(
    "download",
    "Download a whole video",
    args=[
        URL,
        OUTDIR,
        QUIET,
        Arg(
            "quality",
            "Quality",
            flag="-f/--quality",
            kind="choice",
            choices=tuple(QUALITIES),
            default="best",
        ),
    ],
)
def download(
    url: str, outdir: str | None = None, quality: str = "best", quiet: bool = False
) -> int:
    if quality not in QUALITIES:
        raise ChoreboxError(f"Unknown quality {quality!r}; pick one of {', '.join(QUALITIES)}.")

    with console.status("[info]Fetching metadata...", spinner="earth"):
        data = _fetch_info(url)
    if not quiet:
        _print_info(data)

    out = resolve_outdir(outdir)
    stem = safe_stem(data.get("title") or "video")
    before = list(out.iterdir())
    opts = _ydl_opts(quiet)
    opts.update(
        {
            "format": QUALITIES[quality],
            "outtmpl": str(out / f"{stem}.%(ext)s"),
            "ffmpeg_location": require_ffmpeg(),
        }
    )
    if quality == "audio":
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "0"}
        ]
    else:
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            ydl.download([url])
        except yt_dlp.utils.DownloadError as exc:
            raise ChoreboxError(f"Download failed: {exc}") from exc

    _report_written(new_files(out, stem, before), out / stem, quiet)
    return 0


@YT.action(
    "subs",
    "Download subtitles / transcript",
    args=[
        URL,
        OUTDIR,
        QUIET,
        Arg("lang", "Language code", flag="-l/--lang", default="en"),
        Arg("fmt", "Format", flag="-f/--format", kind="choice", choices=SUB_FORMATS, default="txt"),
    ],
)
def subs(
    url: str, outdir: str | None = None, lang: str = "en", fmt: str = "txt", quiet: bool = False
) -> int:
    if fmt not in SUB_FORMATS:
        raise ChoreboxError(f"Unknown format {fmt!r}; pick one of {', '.join(SUB_FORMATS)}.")

    with console.status("[info]Fetching metadata...", spinner="earth"):
        data = _fetch_info(url)
    if not quiet:
        _print_info(data)

    out = resolve_outdir(outdir)
    stem = safe_stem(data.get("title") or "video")
    before = list(out.iterdir())
    opts = _ydl_opts(quiet)
    opts.update(
        {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [lang],
            # Always fetch vtt: srt is a postprocessor away and txt is
            # parsed from it below, so one download covers all three.
            "subtitlesformat": "vtt",
            "outtmpl": str(out / f"{stem}.%(ext)s"),
        }
    )
    if fmt == "srt":
        opts["postprocessors"] = [{"key": "FFmpegSubtitlesConvertor", "format": "srt"}]
        opts["ffmpeg_location"] = require_ffmpeg()

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            ydl.download([url])
        except yt_dlp.utils.DownloadError as exc:
            raise ChoreboxError(f"Subtitle download failed: {exc}") from exc

    written = new_files(out, stem, before)
    if not written:
        raise ChoreboxError(f"No subtitles available for language {lang!r}.")

    if fmt == "txt":
        written = [vtt_to_txt(path) for path in written if path.suffix == ".vtt"]
        if not written:
            raise ChoreboxError("Downloaded subtitles were not in the expected VTT format.")

    _report_written(written, out / stem, quiet)
    return 0


@YT.action(
    "trim",
    "Trim a segment (downloads only that range)",
    args=[
        URL,
        Arg("start", "Start time", flag="-s/--start", default="00:00:00"),
        Arg(
            "end", "End time (blank = one minute in, or the full video if shorter)", flag="-e/--end"
        ),
        Arg("name", "Output filename", flag="-n/--name"),
        OUTDIR,
        QUIET,
    ],
)
def trim(
    url: str,
    start: str = "00:00:00",
    end: str | None = None,
    name: str | None = None,
    outdir: str | None = None,
    quiet: bool = False,
) -> int:
    ffmpeg = require_ffmpeg()
    with console.status("[info]Fetching metadata...", spinner="earth"):
        data = _fetch_info(url)
    if not quiet:
        _print_info(data)

    duration = data.get("duration") or 0
    if end is None:
        end = seconds_to_hms(min(duration, 60) if duration else 60)

    start_s, end_s = hms_to_seconds(start), hms_to_seconds(end)
    if start_s is None or end_s is None:
        raise ChoreboxError("Times must look like HH:MM:SS, MM:SS or a plain seconds count.")
    if start_s >= end_s:
        raise ChoreboxError("Start time must come before end time.")
    if duration and end_s > duration:
        raise ChoreboxError(f"End time is past the video's {seconds_to_hms(duration)} duration.")

    out = resolve_outdir(outdir)
    output_path = (
        Path(name).expanduser() if name else Path(f"{safe_stem(data.get('title') or 'video')}.mp4")
    )
    if output_path.parent == Path("."):
        output_path = out / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    before = list(output_path.parent.iterdir())

    opts = _ydl_opts(quiet)
    opts.update(
        {
            "format": QUALITIES["best"],
            "download_ranges": download_range_func(None, [(start_s, end_s)]),
            "force_keyframes_at_cuts": True,
            "merge_output_format": "mp4",
            # No-op when the merge already produced mp4; a real recode otherwise.
            "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
            "ffmpeg_location": ffmpeg,
            "outtmpl": str(output_path.with_suffix("")) + ".%(ext)s",
        }
    )

    label = f"{seconds_to_hms(start_s)}–{seconds_to_hms(end_s)}"
    if not quiet:
        console.print(f"[info]Trimming {label}...[/info]")
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            ydl.download([url])
        except yt_dlp.utils.DownloadError as exc:
            raise ChoreboxError(f"Trim failed: {exc}") from exc

    written = new_files(output_path.parent, output_path.stem, before)
    _report_written(written or [output_path], output_path, quiet)
    return 0


def vtt_to_txt(vtt_path: Path) -> Path:
    """Strip a WebVTT file down to readable prose next to the original."""
    lines: list[str] = []
    for raw in vtt_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or "-->" in line or line.isdigit():
            continue
        if line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE", "::cue")):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        # Auto-generated captions scroll, so each cue repeats the line above it.
        if line and (not lines or lines[-1] != line):
            lines.append(line)

    txt_path = vtt_path.with_suffix(".txt")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    vtt_path.unlink()
    return txt_path
