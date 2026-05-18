# Inty chat WebSocket REPL

**What you get**: a terminal chat window against a running Inty backend—type a line, send, read the companion’s reply as frames arrive. Bootstrap, memory, inner ticks, and tool use all happen **on the server**; this process only connects, shows text, and helps you debug.

**What you see**: the conversation on your TTY; on **stderr**, structured log lines (timestamps, trace hints) for correlating a turn with Ops / LangSmith. Banner timestamps on screen are plain wall clock, not those log lines.

Setup and run: [AGENTS.md](AGENTS.md).
