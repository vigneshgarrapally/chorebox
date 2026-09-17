"""Importing this package registers every tool as a side effect of import —
see `chorebox.registry`. Add a new tool by adding its import here."""

from . import convert, md2pdf, pdf, video, yt  # noqa: F401
