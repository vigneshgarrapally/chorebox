# chorebox — project context for Claude Code

Read this first in a new session rooted in this repo. It's the handoff
from the session that built the initial version (2026-09-17), spun out of
`vigneshgarrapally/dotfiles`'s `home/tools/toolbox` prototype.

## What this is

A personal CLI for everyday chores that used to mean remembering a
different tool's name each time: trimming a YouTube clip, grabbing a
transcript, decrypting a PDF someone sent, pulling audio out of a local
video, converting a file. One command (`chorebox`), one arrow-key menu,
or subcommands if you want to script it.

**Not** a launcher that shells out to other packages in general — it's a
real Python application. The one exception is `md2pdf`, which bridges to
the separate `prettymd2pdf` repo (Node + Puppeteer) because that one
genuinely can't run inside this process. Everything else is implemented
here.

## Why it's a separate repo from dotfiles

The test that decided it: *"would this be useful on a machine with none
of my personal config?"* Every action here passes — trim a video, decrypt
a PDF, pull a transcript, none of that depends on whose machine it is.
That makes this a product, unlike the thing it replaced
(`home/tools/toolbox` in dotfiles), which was an index of *which tools
this particular person has* and failed that test by construction.

Developed and tested here, independently of any `darwin-rebuild`.

## Packaging: uv, not Nix

Originally packaged as a Nix flake (`pkgs.python3Packages.buildPythonApplication`).
Switched to a plain `pyproject.toml` + `uv.lock` on 2026-09-17: this is a
personal CLI, not something that needs bit-for-bit reproducible builds
across machines, and Nix's syntax/toolchain was overhead relative to `uv`,
which is what most Python contributors already reach for. Install path is
now `uv tool install git+https://github.com/vigneshgarrapally/chorebox`
(or `pip install .`, since it's still a standard package underneath).

This is a real trade-off, not a pure win — two guarantees the Nix build
gave for free are gone now:

- **`ffmpeg` is no longer pinned/wrapped onto `PATH`.** The old flake's
  `wrapProgram --prefix PATH` made chorebox self-contained regardless of
  what the machine had installed — verified at the time by running it
  with `ffmpeg` stripped from `PATH` entirely. Now it's a documented
  prerequisite: `require_ffmpeg()` in `paths.py` just checks `PATH` and
  raises a clear `ChoreboxError` if it's missing. Install it yourself
  (`brew install ffmpeg`).
- **Nothing gates "the build" on tests passing.** `nix build` used to
  fail outright if `pytest` failed, as part of the derivation's check
  phase. `uv` has no equivalent — that gate now has to live in CI (see
  Next steps) rather than at install time.

dotfiles' `home/tools/default.nix` still references this repo as a flake
input from before this switch — that side hasn't been updated yet (see
Next steps).

## Architecture

```
chorebox/
├── registry.py       # the plugin contract: Arg, Action, Tool, tool()
├── console.py         # the one shared Rich console/theme
├── errors.py          # ChoreboxError — reported without a traceback
├── paths.py            # downloads_dir, safe_stem, new_files, require_ffmpeg
├── timeutil.py         # hms_to_seconds / seconds_to_hms
├── cli.py             # argparse + questionary menu, BOTH built from REGISTRY
├── __main__.py         # `python -m chorebox`
└── tools/
    ├── __init__.py    # imports every module below — that import IS the
    │                    registration mechanism
    ├── yt.py           # download / subs / trim / info    — DONE
    ├── pdf.py          # decrypt / batch / compress        — DONE
    ├── video.py        # trim / extract-audio (local file) — DONE
    ├── md2pdf.py       # convert / serve (bridges out)      — DONE, if installed
    └── convert.py      # file                               — STUB, scope undecided
```

### The plugin contract, precisely

A tool module calls `tool(name, label)` once at import time, getting back
a `Tool` object. It registers each command with `@TOOL.action(name, label,
args=[...])` on a plain function `(**kwargs) -> int` (return value is the
process exit code). Each `Arg` is declared once:

```python
Arg(name, prompt, flag=None, kind="text", choices=None, default=None)
```

- `flag=None` → positional CLI arg; `flag="-o/--outdir"` → optional flag.
- `kind` is one of `text | path | choice | password | flag`, and drives
  both the argparse plumbing (`_add_cli_arg` in `cli.py`) *and* which
  questionary prompt the menu uses (`_prompt_for`).
- `name` must match the action function's actual keyword parameter —
  that's the entire binding mechanism, no magic.

**`cli.py` never imports or names a specific tool.** It iterates
`REGISTRY` for both the argparse tree and the menu. Adding a tool is:
write the module, register it, add one import line to
`chorebox/tools/__init__.py`. Nothing else changes. This is the "modular
and pluggable" property that was the actual point of rebuilding this from
the dotfiles prototype.

Actions can be registered with `implemented=False` (see `convert.py`) —
they still show up in `--help` and the menu (marked `[not yet built]`),
calling them raises a clear `ChoreboxError` instead of the command simply
not existing. Use this for anything scaffolded-but-not-built, rather than
leaving a gap silent.

## Status, precisely, and what was actually verified

Everything marked "done" below was run for real in the session that built
it — not just unit-tested. Specifics, since "it works" is worth less than
what was actually checked:

- **`yt info/download/subs/trim`** — run against a real, tiny YouTube
  video. Metadata came back correct. `trim -s 3 -e 8` produced a clip
  `ffprobe` measured at exactly the requested length. `subs --format txt`
  produced clean prose (the VTT→txt conversion has two dedicated tests:
  `tests/test_vtt.py`). `download --quality audio` produced a real `.m4a`.
- **`pdf decrypt/batch`** — fixtures encrypted with `pikepdf` itself, run
  through `decrypt`, then **reopened with no password** to confirm
  `is_encrypted == False`. Batch handles a mixed folder correctly (wrong
  password, already-plain, already-exists-without-`--force`) and refuses
  to write into the source directory.
- **`pdf compress`** — real stream recompression via
  `pikepdf`/`qpdf` (`compress_streams` + `object_stream_mode=generate`).
  On a 30-page test fixture: 7 KB → 2 KB (67% smaller). This is *not*
  image recompression (see Known limitations below) — most of the win
  here is on PDFs with bloated/uncompressed object streams.
- **`video trim/extract-audio`** — run against a real local clip.
  `extract-audio --format mp3` produced a real, playable-sized MP3.
  `trim` is a fast stream-copy cut (`-c copy`); asked for a 2.0s segment,
  got 2.2s — see Known limitations.
- **The menu itself** — driven end-to-end through a pty (arrow keys,
  selection, prompts, password masking) for both the top-level tool list
  and a stub action's `[not yet built]` label. Confirmed the generic
  `_prompt_for`/`_run_action` machinery works, not just the individual
  tool functions (those share the same code path as the CLI, already
  covered above).
- **The Nix→uv switch (2026-09-17)** — `uv lock` resolved cleanly, `uv
  sync --group dev` built and installed chorebox into a fresh `.venv`,
  `uv run pytest` passed all 19 tests, and `uv run chorebox --help`
  produced the expected subcommand list. This confirms the package is
  sound under `uv`. It does *not* re-verify the individual tool actions
  (`yt`, `pdf`, `video`) against real files or re-confirm the
  `ffmpeg`-stripped-`PATH` case above — that guarantee no longer exists
  post-switch (see Packaging), and the switch touched packaging only, not
  the tool code itself.
- **`convert file`** — deliberately not built. Registered as a stub so
  the gap is visible rather than silent (see Next steps).

## Known limitations (not bugs — documented trade-offs)

- **`video trim`** uses `-c copy` for speed and losslessness, so cuts snap
  to the nearest keyframe — expect slack of up to a second or two, not
  frame accuracy. A `--accurate` re-encode mode (`-c:v libx264 -c:a aac`,
  slower, exact) is a natural follow-up, not yet built.
- **`pdf compress`** only recompresses PDF-internal streams/objects. It
  does not re-encode embedded images — that needs something like
  Ghostscript. Real compression on text-heavy PDFs, modest on
  image-heavy scans.
- **`convert file`** is unscoped and unbuilt on purpose (see Next steps).
- **`ffmpeg` is an unenforced prerequisite**, not a pinned/bundled one.
  `uv` can't wrap a non-Python system binary onto `PATH` the way the old
  Nix build did — `require_ffmpeg()` (`paths.py`) just checks and raises
  a clear error if it's missing. Documented, not a bug, but a genuine
  regression from the guarantee the Nix build used to provide (see
  Packaging).

## Next steps (in the order I'd tackle them)

1. **Decide `convert`'s scope.** "Convert file types" was requested
   without specifics. Needs a real answer before writing code: image
   formats (png/webp/heic/avif)? Documents (docx→pdf, pdf→docx)? Video
   containers (would overlap `video`)? Pick a first slice, don't try to
   cover all of it at once.
2. **`video trim --accurate`** — the re-encode fallback described above,
   for when keyframe-snapping isn't acceptable.
3. **`pdf compress`, heavier mode** — optionally shell out to
   Ghostscript (`gs -dPDFSETTINGS=/ebook ...`) for real image
   recompression, behind a flag, since the current default is honest
   about being modest.
4. **CI.** No GitHub Actions yet. A single job running
   `uv sync --group dev && uv run pytest && uv run ruff check .` on push
   would catch regressions before they reach dotfiles. This matters more
   now than it did under Nix — `uv` has no build-time test gate
   equivalent to `nix build`'s check phase, so without CI nothing blocks
   a broken commit from landing.
5. **Repo visibility.** Currently **private**. Flip to public with
   `gh repo edit --visibility public` whenever you want it discoverable
   (matches the `prettymd2pdf` precedent) — nothing here depends on it
   staying private.
6. **dotfiles-side wiring.** `home/tools/default.nix` in dotfiles still
   references this repo as a flake input from before the Nix→uv switch.
   That needs to change to something like a
   `uv tool install git+https://github.com/vigneshgarrapally/chorebox`
   step (e.g. in a home-manager activation script) instead. Not started
   — this repo's side of the switch is done, dotfiles' isn't.

## Conventions

- `uv run ruff check . && uv run ruff format .` before committing —
  `pyproject.toml` sets line-length 100, everything else default.
- Commit `uv.lock` alongside any dependency change in `pyproject.toml` —
  it's the reproducibility guarantee now that Nix's `flake.lock` is gone.
  Regenerate it with `uv lock`.
- Tests are pure-logic only (`timeutil`, `paths`, `vtt_to_txt`, the
  registry contract itself, `cli.build_parser()` wiring). No tests hit
  the network or shell out to `ffmpeg`/`yt-dlp`/`pikepdf` against real
  files — that was verified manually once per the Status section above,
  not re-verified on every `pytest` run. If that manual-verification
  boundary stops feeling right as this grows, revisit it explicitly
  rather than silently adding flaky network tests.
- `Arg.name` must equal the action function's actual parameter name —
  there is no separate mapping table, so a mismatch is a `TypeError` at
  call time, not a silent bug. If you add an `Arg`, check the function
  signature right next to it.
- New tool module → `tool()` call → register in
  `chorebox/tools/__init__.py`. If you're touching `cli.py` to add a
  tool, something's wrong — that file should only ever change for
  genuinely new *kinds* of `Arg` (a new `kind=` value), not new tools.
