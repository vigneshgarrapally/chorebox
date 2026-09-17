"""Generic file-type conversion — deliberately unscoped.

STUB. "Convert file types" was requested without specifics: image formats
(png/webp/heic)? Documents (docx/pdf)? Video containers (that overlaps with
`video` already)? This needs a scoping conversation before it's built — see
CLAUDE.md → Next steps. Registered anyway so the gap is visible in --help
and the menu instead of silently not existing.
"""

from ..errors import ChoreboxError
from ..registry import Arg, tool

CONVERT = tool("convert", "Convert files")


@CONVERT.action(
    "file",
    "Convert a file from one format to another",
    args=[Arg("file", "Input file", kind="path"), Arg("to", "Target format", flag="-t/--to")],
    implemented=False,
)
def convert_file(file: str, to: str | None = None) -> int:
    raise ChoreboxError(
        "Not implemented yet — 'convert' needs its scope decided first "
        "(which formats, in which direction?). See CLAUDE.md → Next steps."
    )
