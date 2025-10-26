"""
Wrapper for langchain.
We should only use exposed functions and classes from this module.
"""

from langchain_postgres import PostgresChatMessageHistory as LCChatHistory
# 最多当从该模块用 * 导入时才公开类
# 这是为了避免未使用的导入出现 lint 警告
#还有利于IDE自动完成
__all__ = ["LCChatHistory"]
