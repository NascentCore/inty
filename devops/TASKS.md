# 与运维相关的任务

- [ ] z@sxwl.ai 改为 unpaid admin，然后建立个人的 max plan <img width="600" height="864" alt="image" src="https://github.com/user-attachments/assets/2f8359dd-28e1-435a-b57e-72d6ae0fc410" />

- [ ] 对接飞书 MCAP <https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/mcp_integration/mcp_introduction>

- [ ] 创建新的 dev-intellimate GCE VM 实例
  - [ ] 调查故障诱因
  - [ ] 将 inty-dev 实例迁移到该实例上，需要修改 DNS 映射
  - [ ] 将 self-hosted runner 迁移到 dev-intellimate GCE VM 实例上

- [ ] 在数据库实例中，打开流式数据同步，从而保证副本中的数据实时性
  <img width="800" height="228" alt="image" src="https://github.com/user-attachments/assets/dbcee2db-7ee4-4f9e-af77-74eada343efe" />

- [ ] **删除废弃的 `messages` 表**（减少误解：实际聊天消息存于 `chat_history`）
  - 背景：`app/models/message.py` 中 `Message` 对应表 `messages` 已标注 DEPRECATED，从未被使用；业务聊天数据均在 `chat_history` 表。
  - 步骤概要：
    1. 新增 Alembic 迁移：仅执行 `DROP TABLE IF EXISTS messages CASCADE`（不改动历史迁移）。
    2. 移除 ORM：删除或精简 `app/models/message.py` 中的 `Message` 类；从 `app/models/__init__.py` 去掉对 `Message` 的导入；在 `app/models/user.py`、`app/models/agent.py` 中删除与 `Message` 的 relationship。
    3. 若 `app/schemas/chat.py` 仍使用 `MessageType`、`SenderType`，将两枚举迁至 schema 层或独立小模块后，再移除对 DB 模型 `Message` 的依赖。
    4. 更新 `tools/scripts/cleanup_agents_and_chats.py`：从表列表中移除 `messages`，删除对 `messages` 的 `DELETE` 及 `after_counts["messages"]` 校验。
  - 参考：此前在 Ask 模式下对「messages 表是否可以被删除」的结论与依赖梳理。
