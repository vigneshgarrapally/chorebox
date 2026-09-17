"""The one shared Rich console every tool module prints through."""

from rich.console import Console
from rich.theme import Theme

console = Console(
    theme=Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "success": "bold green",
            "url": "underline blue",
            "muted": "dim",
        }
    )
)
