"""The plugin contract every tool module implements.

A tool module calls `tool()` once at import time to register itself, then
`.action()` per command it offers. `chorebox.tools` imports every module
purely for that side effect — the registry, not the import graph, is the
API. `cli.py` never mentions "yt" or "pdf" by name; it only ever iterates
`REGISTRY`. That's what makes adding a tool a one-file change: write a
module, register it here, done.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

ActionFn = Callable[..., int]

# The whole plugin surface. Every action's inputs are described once, in
# this shape, and read by both the CLI and the interactive menu — neither
# is a second implementation of the other that could drift out of sync.
ArgKind = str  # "text" | "path" | "choice" | "password" | "flag"


@dataclass
class Arg:
    """One input an action needs. Becomes an argparse flag (or positional,
    if `flag` is None) *and* a menu prompt, from the same declaration."""

    name: str  # kwarg name the action function receives
    prompt: str  # menu question text / CLI --help text
    flag: str | None = None  # e.g. "-o/--outdir"; None = positional CLI arg
    kind: ArgKind = "text"
    choices: tuple[str, ...] | None = None  # required when kind == "choice"
    default: Any = None


@dataclass
class Action:
    name: str  # subcommand name, e.g. "trim"
    label: str  # menu label, e.g. "Trim a segment"
    fn: ActionFn
    args: list[Arg] = field(default_factory=list)
    implemented: bool = True  # False = registered, not built yet (shows in
    # --help and the menu so the surface is honest about what's missing,
    # instead of the action just not existing anywhere)


@dataclass
class Tool:
    name: str  # e.g. "yt"
    label: str  # e.g. "YouTube"
    actions: list[Action] = field(default_factory=list)

    def action(
        self,
        name: str,
        label: str,
        args: list[Arg] | None = None,
        implemented: bool = True,
    ):
        """Decorator: register the wrapped function as one of this tool's
        actions. Usage:

            YT = tool("yt", "YouTube")

            @YT.action("info", "Show metadata", args=[URL])
            def info(url):
                ...
                return 0
        """

        def wrap(fn: ActionFn) -> ActionFn:
            self.actions.append(
                Action(
                    name=name,
                    label=label,
                    fn=fn,
                    args=args or [],
                    implemented=implemented,
                )
            )
            return fn

        return wrap


REGISTRY: dict[str, Tool] = {}


def tool(name: str, label: str) -> Tool:
    """Register a new tool group. Call once per module, at import time."""
    t = Tool(name=name, label=label)
    REGISTRY[name] = t
    return t
