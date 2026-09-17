"""Filesystem helpers shared across tool modules: output dirs, safe
filenames, and detecting "what got written" without an fd to track."""

import glob as globlib
import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from .errors import ChoreboxError


def downloads_dir() -> Path:
    """~/Downloads on macOS, ~/downloads elsewhere — whichever exists."""
    for name in ("Downloads", "downloads"):
        candidate = Path.home() / name
        if candidate.is_dir():
            return candidate
    return Path.home() / "downloads"


def resolve_outdir(value: str | None) -> Path:
    directory = Path(value).expanduser() if value else downloads_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ChoreboxError(
            "ffmpeg not found on PATH. It's wrapped into chorebox's own Nix "
            "closure (see flake.nix) — outside Nix, install it yourself."
        )
    return ffmpeg


def safe_stem(title: str) -> str:
    stem = re.sub(r'[\\/*?:"<>|]', "", title)
    return "_".join(stem.split()).strip()[:100] or "output"


def new_files(directory: Path, stem: str, before: Sequence[Path]) -> list[Path]:
    """Files matching `stem.*` in `directory` that weren't there before."""
    pattern = str(directory / (globlib.escape(stem) + ".*"))
    seen = set(before)
    return sorted(p for p in map(Path, globlib.glob(pattern)) if p not in seen)
