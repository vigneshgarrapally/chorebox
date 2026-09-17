"""Bridges to the sibling `prettymd2pdf` project's CLI, if it's on PATH.

Not vendored: different language (Node + Puppeteer), its own repo, its own
release cycle — see the architecture note in CLAUDE.md for why that split
is deliberate. https://github.com/vigneshgarrapally/prettymd2pdf
"""

import shutil
import subprocess

from ..errors import ChoreboxError
from ..registry import Arg, tool

MD2PDF = tool("md2pdf", "Markdown → PDF")


def _binary() -> str:
    exe = shutil.which("prettymd2pdf")
    if not exe:
        raise ChoreboxError(
            "prettymd2pdf isn't on PATH. Install it — "
            "https://github.com/vigneshgarrapally/prettymd2pdf — or add it "
            "as a flake input in dotfiles' home/tools/default.nix."
        )
    return exe


@MD2PDF.action(
    "convert",
    "Convert a markdown file to PDF",
    args=[
        Arg("file", "Markdown file", kind="path"),
        Arg("output", "Output PDF path (blank = default naming)", flag="-o/--output"),
        Arg("title", "Title (blank = first # heading)", flag="--title"),
        Arg("org", "Kicker line above the title", flag="--org"),
        Arg("accent", "Accent color, hex (blank = default)", flag="--accent"),
    ],
)
def convert(
    file: str,
    output: str | None = None,
    title: str | None = None,
    org: str | None = None,
    accent: str | None = None,
) -> int:
    cmd = [_binary(), file]
    if output:
        cmd += ["-o", output]
    if title:
        cmd += ["--title", title]
    if org:
        cmd += ["--org", org]
    if accent:
        cmd += ["--accent", accent]
    return subprocess.run(cmd, check=False).returncode


@MD2PDF.action("serve", "Start the local web UI (paste markdown, live preview)", args=[])
def serve() -> int:
    return subprocess.run([_binary(), "serve"], check=False).returncode
