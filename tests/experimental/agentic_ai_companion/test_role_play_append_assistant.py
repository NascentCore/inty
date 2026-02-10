# 覆盖 experimental/agentic_ai_companion/role_play_minimal 中「out.done 时是否追加 assistant」的规则，
# 不导入该模块以免依赖 .env 与 app。规则与 role_play_minimal.run_repl 内逻辑一致。
#
# 手动验证：在仓库根目录执行 python -m experimental.agentic_ai_companion.main，
# 1) 输入「Hello」→ 无工具调用，对话历史应以一条 assistant 结尾；
# 2) 输入「发我 app 图标」→ 触发 send_app_icon，对话历史应以 tool 结尾，无重复 assistant。

import pytest


def _should_append_assistant_when_done(messages: list[dict]) -> bool:
    """与 role_play_minimal 中一致：仅当 messages 最后一条是 user 时追加（无工具调用）；最后是 tool 时不再追加。"""
    return messages[-1]["role"] == "user"


@pytest.mark.unit
def test_append_assistant_when_done_without_tool_call():
    """无工具调用：API 直接返回 content，out.messages 仍以 user 结尾，应追加 assistant。"""
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ]
    assert _should_append_assistant_when_done(messages) is True


@pytest.mark.unit
def test_do_not_append_assistant_when_done_after_tool_call():
    """有工具调用且 TERMINAL：out.messages 已含 assistant+tool，不应再追加。"""
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Send me the app icon"},
        {"role": "assistant", "content": "Here you are.", "tool_calls": [{"id": "1", "function": {"name": "send_app_icon", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "1", "content": "已发送图片。"},
    ]
    assert _should_append_assistant_when_done(messages) is False
