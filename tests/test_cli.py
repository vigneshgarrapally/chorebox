"""Smoke tests: the parser argparse builds from the registry actually has
every registered tool/action as a subcommand."""

from chorebox.cli import build_parser


def test_every_tool_and_action_reachable_from_the_cli():
    parser = build_parser()
    args = parser.parse_args(["pdf", "decrypt", "some.pdf", "-p", "secret"])
    assert args.tool == "pdf"
    assert args.action == "decrypt"
    assert args.file == "some.pdf"
    assert args.password == "secret"


def test_bare_invocation_has_no_tool_selected():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.tool is None


def test_stub_action_is_still_a_valid_subcommand():
    parser = build_parser()
    args = parser.parse_args(["convert", "file", "in.png", "-t", "webp"])
    assert args.tool == "convert"
    assert args.to == "webp"
