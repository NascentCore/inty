"""
Wrapper for langchain.
We should only use exposed functions and classes from this module.
"""

from langchain_postgres import PostgresChatMessageHistory as LCChatHistory

CHAT_HISTORY_TABLE_NAME = "chat_history"

# Only expose the classes when imported with * from this module
# This is to avoid lint warning for unused import
# And it also helps with IDE auto-completion
__all__ = ["LCChatHistory", "CHAT_HISTORY_TABLE_NAME"]
