"""Contract tests for the plugin registry — the thing that makes adding a
tool a one-module change rather than a cli.py change."""

from chorebox.registry import REGISTRY


def test_every_shipped_tool_is_registered():
    assert set(REGISTRY) == {"yt", "pdf", "video", "md2pdf", "convert"}


def test_every_action_is_callable_and_has_a_label():
    for t in REGISTRY.values():
        assert t.actions, f"tool {t.name!r} registered with zero actions"
        for act in t.actions:
            assert callable(act.fn)
            assert act.label


def test_stubbed_actions_are_marked_not_implemented():
    convert_actions = {a.name: a for a in REGISTRY["convert"].actions}
    assert convert_actions["file"].implemented is False


def test_choice_args_declare_their_choices():
    for t in REGISTRY.values():
        for act in t.actions:
            for arg in act.args:
                if arg.kind == "choice":
                    assert arg.choices, (
                        f"{t.name} {act.name} arg {arg.name!r} is a choice with no choices"
                    )
