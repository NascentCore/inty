from tools.inty_v2_repl.backend_chat_ws import reconnect_delay_sec


def test_reconnect_delay_sec_exponential_cap() -> None:
    assert reconnect_delay_sec(0, initial=1.0, cap=100.0) == 1.0
    assert reconnect_delay_sec(1, initial=1.0, cap=100.0) == 2.0
    assert reconnect_delay_sec(2, initial=1.0, cap=100.0) == 4.0
    assert reconnect_delay_sec(10, initial=1.0, cap=100.0) == 100.0
