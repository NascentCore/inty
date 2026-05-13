# User preferences

**User's general preferences, not specific rules or certain cases**

- Companion WebSocket：**产品约定**隐式问候用 **`user_signed_on` + `implicit_greeting` + `message_id`**；不在服务端对 **`IMPLICIT_USER_SIGNED_ON`** 聊天帧做 wire 预拒绝（与内部 synthetic 一致）。
