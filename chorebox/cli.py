"""argparse subcommands *and* a questionary menu, both generated from the
tool registry (`chorebox.registry`). Neither is a second implementation of
the other: the menu builds the same kwargs dict an action function
receives; argparse parses straight into one. Add a tool by writing a
module under `chorebox/tools/` that calls `registry.tool()` — this file
never changes.
"""

import argparse
from collections.abc import Sequence

import questionary
from questionary import Choice
from rich.panel import Panel

from . import __version__, tools  # noqa: F401 — import triggers registration
from .console import console
from .errors import ChoreboxError
from .registry import REGISTRY, Action, Arg, Tool


def ask(prompt, *args, **kwargs):
    """Run a questionary prompt, treating Ctrl-C / Esc as a cancel."""
    answer = prompt(*args, **kwargs).ask()
    if answer is None:
        raise KeyboardInterrupt
    return answer


# --- argparse, generated from the registry ---


def _add_cli_arg(parser: argparse.ArgumentParser, a: Arg) -> None:
    kwargs = {"help": a.prompt}
    if a.kind == "flag":
        kwargs["action"] = "store_true"
    else:
        if a.choices:
            kwargs["choices"] = list(a.choices)
        if a.default is not None:
            kwargs["default"] = a.default
    if a.flag:
        parser.add_argument(*a.flag.split("/"), dest=a.name, **kwargs)
    else:
        parser.add_argument(a.name, **kwargs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chorebox",
        description="Personal CLI for everyday chores. Run with no arguments for a menu.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"chorebox {__version__}")
    tool_subs = parser.add_subparsers(dest="tool")

    for tool_name, t in REGISTRY.items():
        tool_parser = tool_subs.add_parser(tool_name, help=t.label)
        action_subs = tool_parser.add_subparsers(dest="action", required=True)
        for act in t.actions:
            help_text = act.label if act.implemented else f"{act.label} [not yet built]"
            act_parser = action_subs.add_parser(act.name, help=help_text)
            for a in act.args:
                _add_cli_arg(act_parser, a)

    return parser


def dispatch(args: argparse.Namespace) -> int:
    t = REGISTRY[args.tool]
    act = next(a for a in t.actions if a.name == args.action)
    if not act.implemented:
        raise ChoreboxError(f"'{t.name} {act.name}' isn't built yet — see CLAUDE.md.")

    kwargs = {}
    for a in act.args:
        value = getattr(args, a.name)
        if a.kind == "password" and not value:
            value = ask(questionary.password, f"{a.prompt}:")
        kwargs[a.name] = value
    return act.fn(**kwargs)


# --- questionary menu, driven by the same registry ---


def _prompt_for(a: Arg):
    if a.kind == "password":
        return ask(questionary.password, f"{a.prompt}:")
    if a.kind == "flag":
        return ask(questionary.confirm, a.prompt, default=bool(a.default))
    if a.kind == "choice":
        return ask(questionary.select, f"{a.prompt}:", choices=list(a.choices or []))
    if a.kind == "path":
        return ask(questionary.path, f"{a.prompt}:", default=a.default or "")
    return ask(questionary.text, f"{a.prompt}:", default=a.default or "")


def _run_action(act: Action) -> int:
    if not act.implemented:
        console.print(f"[warning]'{act.label}' isn't built yet.[/warning]")
        return 0
    kwargs = {a.name: _prompt_for(a) for a in act.args}
    return act.fn(**kwargs)


def _menu_for(t: Tool) -> int:
    while True:
        choices = [
            Choice(a.label if a.implemented else f"{a.label}  [not yet built]", a.name)
            for a in t.actions
        ] + [Choice("← Back", "__back__")]
        picked = ask(questionary.select, f"{t.label} — what do you want to do?", choices=choices)
        if picked == "__back__":
            return 0
        act = next(a for a in t.actions if a.name == picked)
        try:
            return _run_action(act)
        except ChoreboxError as exc:
            console.print(f"[error]✗ {exc}[/error]", soft_wrap=True)
            return 1


def run_menu() -> int:
    console.print(
        Panel.fit(
            f"[bold cyan]chorebox[/bold cyan] [muted]v{__version__}[/muted]", border_style="cyan"
        )
    )
    exit_code = 0
    while True:
        choices = [Choice(t.label, name) for name, t in REGISTRY.items()] + [
            Choice("Quit", "__quit__")
        ]
        picked = ask(questionary.select, "Pick a tool:", choices=choices)
        if picked == "__quit__":
            return exit_code
        try:
            exit_code = _menu_for(REGISTRY[picked])
        except KeyboardInterrupt:
            console.print("[muted]Cancelled.[/muted]")
        console.print()


def main(argv: Sequence[str] | None = None) -> int:
    # Caught here, not just in __main__.py's `if __name__ == "__main__"`
    # block: the installed `chorebox` binary is a setuptools console-script
    # wrapper that calls this function directly, never that block. A Ctrl-C
    # during a long download (CLI mode, no menu prompt in the way) needs to
    # land here to get the friendly message instead of a raw traceback.
    args = build_parser().parse_args(argv)
    try:
        return run_menu() if args.tool is None else dispatch(args)
    except ChoreboxError as exc:
        console.print(f"[error]✗ {exc}[/error]", soft_wrap=True)
        return 1
    except KeyboardInterrupt:
        console.print("\n[warning]Aborted.[/warning]")
        return 130
