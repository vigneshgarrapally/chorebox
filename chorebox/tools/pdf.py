"""PDF actions: decrypt (single/batch), compress.

decrypt/batch ported unchanged from the verified dotfiles-era prototype —
tested against real pikepdf-encrypted fixtures, including confirming the
output reopens with no password. `compress` is new here.
"""

import warnings
from pathlib import Path

import pikepdf
from rich.table import Table

from ..console import console
from ..errors import ChoreboxError
from ..registry import Arg, tool

PDF = tool("pdf", "PDF")

OK_STATUSES = ("decrypted", "copied (not encrypted)")

FILE = Arg("file", "PDF file", kind="path")
PASSWORD = Arg("password", "Password", flag="-p/--password", kind="password")
OUTPUT = Arg("output", "Output path (blank = default naming)", flag="-o/--output")
FORCE = Arg("force", "Overwrite existing output?", flag="--force", kind="flag")


def _decrypt_one(src: Path, password: str, dest: Path, force: bool) -> str:
    """Decrypt `src` to `dest`. Returns a short status word for the report."""
    if dest.exists() and not force:
        return "skipped (already exists — use --force)"
    try:
        with warnings.catch_warnings():
            # pikepdf warns when a password is supplied for an already-plain
            # PDF — a normal case in a batch, not something to shout about.
            warnings.filterwarnings("ignore", "A password was provided", UserWarning)
            with pikepdf.open(src, password=password) as pdf:
                encrypted = pdf.is_encrypted
                dest.parent.mkdir(parents=True, exist_ok=True)
                pdf.save(dest)
    except pikepdf.PasswordError:
        return "wrong password"
    except pikepdf.PdfError as exc:
        return f"error: {exc}"
    return "decrypted" if encrypted else "copied (not encrypted)"


@PDF.action("decrypt", "Decrypt one PDF", args=[FILE, PASSWORD, OUTPUT, FORCE])
def decrypt(file: str, password: str, output: str | None = None, force: bool = False) -> int:
    src = Path(file).expanduser()
    if not src.is_file():
        raise ChoreboxError(f"No such file: {src}")
    dest = Path(output).expanduser() if output else src.with_name(f"{src.stem}-decrypted.pdf")
    if dest.is_dir():
        dest = dest / f"{src.stem}-decrypted.pdf"
    status = _decrypt_one(src, password, dest, force)
    if status in OK_STATUSES:
        console.print(f"[success]✓ {status}[/success] [url]{dest.resolve()}[/url]", soft_wrap=True)
        return 0
    console.print(f"[error]✗ {src.name}: {status}[/error]", soft_wrap=True)
    return 1


@PDF.action(
    "batch",
    "Decrypt every PDF in a folder",
    args=[Arg("directory", "Folder of PDFs", kind="path"), PASSWORD, OUTPUT, FORCE],
)
def batch(directory: str, password: str, output: str | None = None, force: bool = False) -> int:
    src_dir = Path(directory).expanduser()
    if not src_dir.is_dir():
        raise ChoreboxError(f"No such directory: {src_dir}")
    sources = sorted(p for p in src_dir.glob("*.pdf") if p.is_file())
    if not sources:
        raise ChoreboxError(f"No .pdf files in {src_dir}")

    outdir = Path(output).expanduser() if output else src_dir / "decrypted"
    if outdir.resolve() == src_dir.resolve():
        raise ChoreboxError(
            "Output directory is the source directory — that would overwrite the originals."
        )
    outdir.mkdir(parents=True, exist_ok=True)
    console.print(f"[muted]{len(sources)} PDFs → {outdir}[/muted]", soft_wrap=True)

    table = Table(box=None, padding=(0, 2))
    table.add_column("File")
    table.add_column("Result")
    failures = 0
    for src in sources:
        status = _decrypt_one(src, password, outdir / src.name, force)
        ok = status in OK_STATUSES
        failures += 0 if ok else 1
        style = "success" if status == "decrypted" else "muted" if ok else "error"
        table.add_row(src.name, f"[{style}]{status}[/{style}]")
    console.print(table)
    return 1 if failures else 0


@PDF.action(
    "compress",
    "Shrink a PDF by recompressing its internal streams",
    args=[FILE, Arg("output", "Output path (blank = default naming)", flag="-o/--output")],
)
def compress(file: str, output: str | None = None) -> int:
    """Stream-level recompression via pikepdf/qpdf — real, but modest. It
    does not re-encode embedded images (that needs Ghostscript or similar);
    biggest wins are on PDFs with bloated/uncompressed object streams. A
    heavier image-recompression mode is a documented follow-up."""
    src = Path(file).expanduser()
    if not src.is_file():
        raise ChoreboxError(f"No such file: {src}")
    dest = Path(output).expanduser() if output else src.with_name(f"{src.stem}-compressed.pdf")

    before_size = src.stat().st_size
    with pikepdf.open(src) as pdf:
        pdf.save(
            dest,
            compress_streams=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )
    after_size = dest.stat().st_size
    pct = 100 * (1 - after_size / before_size) if before_size else 0

    console.print(
        f"[success]✓ {before_size / 1024:.0f} KB → {after_size / 1024:.0f} KB "
        f"({pct:.0f}% smaller)[/success] [url]{dest.resolve()}[/url]",
        soft_wrap=True,
    )
    return 0
