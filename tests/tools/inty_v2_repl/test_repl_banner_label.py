"""REPL assistant metadata section label from WS ``meta_data``."""

from tools.inty_v2_repl.main import _repl_assistant_banner_label


def test_repl_banner_label_greeting_from_meta_source() -> None:
    assert (
        _repl_assistant_banner_label(
            None,
            meta_data={"source": "greeting", "user_msg_uuid": "u1"},
        )
        == "greeting"
    )


def test_repl_banner_label_inner_tick_activity_beats_greeting_source() -> None:
    assert (
        _repl_assistant_banner_label(
            None,
            meta_data={
                "source": "greeting",
                "inner_tick_activity": "maintenance",
            },
        )
        == "inner-tick maintenance"
    )
