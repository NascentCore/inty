"""Terminal client for the Inty chat WebSocket.

The REPL behaves like an external app client: it reads local connection
settings, sends typed lines to the chat WebSocket, and prints server frames
without importing companion harness internals or backend process configuration.
"""
