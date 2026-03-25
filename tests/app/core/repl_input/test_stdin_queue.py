import io

from app.core.repl_input.stdin_queue import spawn_stdin_line_reader


def test_spawn_stdin_line_reader_reads_until_eof() -> None:
    buf = io.StringIO("first\nsecond\n")
    q, thread = spawn_stdin_line_reader(stdin=buf)
    assert q.get() == ("first", False)
    assert q.get() == ("second", False)
    assert q.get() is None
    thread.join(timeout=2.0)
    assert not thread.is_alive()
