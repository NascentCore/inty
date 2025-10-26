# prompting

Prompting，提示词工程，指通过输入提示词来改变大模型行为，目的是支持Inty角色扮演的功能。

## 光标摘要

- 目录用途：组织角色扮演场景中的提示词集合，提供聊天/智能体逻辑组合调用。
- 关键文件：`characters.py`、`personalities.py`、`traits.py`、`verbals.py`、`actions.py` 等素材脚本。
- 关联: `app/core/agent` 中的提示组合与 `app/services/chat_service.py` 的推理流程。
