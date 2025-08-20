"""
Wrapper for langchain.
We should only use exposed functions and classes from this module.
"""

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_postgres import PostgresChatMessageHistory as LCChatHistory


# Based on the OpenAI Python SDK, we should use the following roles:
# https://github.com/openai/openai-python?tab=readme-ov-file

# Role is a concept to refer to conceptual entity played out in a chat.
# Their content is input to the LLM, and the LLM's response is to complete the assistant role's
# response to user role's input, based on the system role's settings.
# All of the content along with the role is the input to the LLM, which can be called prompt as well.
ROLE = "role"

# Content is the information of a role, and is sent to the LLM.
CONTENT = "content"

# The role for specifying the system prompt, or directives.
SYSTEM_ROLE = "system"
# The role referring to the user.
USER_ROLE = "user"
# The role played by the LLM.
ASSISTANT_ROLE = "assistant"


def to_openai_message(langchain_message: BaseMessage) -> dict:
    if isinstance(langchain_message, SystemMessage):
        return {ROLE: SYSTEM_ROLE, CONTENT: langchain_message.content}
    elif isinstance(langchain_message, HumanMessage):
        return {ROLE: USER_ROLE, CONTENT: langchain_message.content}
    elif isinstance(langchain_message, AIMessage):
        return {ROLE: ASSISTANT_ROLE, CONTENT: langchain_message.content}
    else:
        raise ValueError(
            f"Unsupported message type: {type(langchain_message)} {langchain_message}"
        )
