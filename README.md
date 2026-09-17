# chorebox

Personal CLI for everyday chores — video trimming, transcripts, PDF
cleanup, file conversion — one command, one menu, instead of remembering a
different tool's name for each.

Run it bare for an arrow-key menu, or pass subcommands to skip the menu
and script it. Both surfaces are generated from the same place (see
[Architecture](#architecture)), so they never drift apart.

```bash
chorebox                                                  # interactive menu
chorebox yt trim "URL" --start 00:01:00 --end 00:02:00    # a YouTube segment
chorebox yt subs "URL" --lang en --format txt             # transcript
chorebox pdf decrypt locked.pdf                           # prompts for the password, hidden
chorebox pdf compress big.pdf                             # shrink via stream recompression
chorebox video trim clip.mov --start 3 --end 8             # trim a local file
chorebox video extract-audio clip.mov --format mp3
chorebox md2pdf convert notes.md                          # bridges to prettymd2pdf, if installed
```

## Install

Via [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv tool install git+https://github.com/vigneshgarrapally/chorebox
```

Or from a local checkout:

```bash
uv tool install .
```

Either way, `ffmpeg` needs to already be on your `PATH` yourself (e.g.
`brew install ffmpeg`) — chorebox doesn't bundle it.

Plain `pip` also works, since it's a regular `pyproject.toml` package:

```bash
pip install .
```

## What's here today

| Tool | Actions | Status |
|---|---|---|
| `yt` | `download`, `subs`, `trim`, `info` | done |
| `pdf` | `decrypt`, `batch`, `compress` | done |
| `video` | `trim`, `extract-audio` | done (see caveats below) |
| `md2pdf` | `convert`, `serve` | done, if [`prettymd2pdf`](https://github.com/vigneshgarrapally/prettymd2pdf) is installed |
| `convert` | `file` | **not built yet** — registered as a stub so the gap is visible in `--help` and the menu, instead of the command just not existing |

See [CLAUDE.md](./CLAUDE.md) for the fuller status writeup, known caveats
(e.g. `video trim`'s keyframe-snapping), and the open backlog.

## Architecture

Every tool is a module under `chorebox/tools/` that registers itself with
a small plugin contract (`chorebox/registry.py`): a `Tool` with a list of
`Action`s, each `Action` declaring its `Arg`s once. `chorebox/cli.py`
builds *both* the argparse subcommands and the questionary menu from that
same registry — it never mentions `yt` or `pdf` by name. Adding a tool is
one new module plus one import line in `chorebox/tools/__init__.py`;
`cli.py` doesn't change.

Everything here is Python, so it's one package with internal modules —
not the "shell out to a separate binary per tool" pattern you'd need if a
tool were in a different language (that's what `md2pdf` does, bridging to
`prettymd2pdf`'s own Node binary, since that one genuinely can't live
inside this process).

## Why this is its own repo, not folded into dotfiles

Every action here (trim a video, decrypt a PDF, get a transcript) is
useful on a machine with zero of my personal config — it's a product, not
an index of my machine. That's the line: `home/tools/toolbox` in
dotfiles was retired in favor of this repo for exactly that reason.
Developed and tested here independently of any `darwin-rebuild`.

## Development

```bash
uv sync --group dev       # venv with all deps + pytest + ruff
uv run pytest             # 19 tests, pure-logic only — no network, no ffmpeg
uv run ruff check . && uv run ruff format --check .
```

## License

MIT
