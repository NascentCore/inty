# 对外 HTTP / WebSocket 端点实现

## Agentic companion

This is the new paradigm of companionship.
The old http-based paradigm is roleplay.

## 全局纪律

- **超级用户**：后台/运营向能力必须 **严格鉴权**，默认仅 **superuser** 可达。
- **契约同步**：改路径、方法或语义时，更新 **Pydantic schema、OpenAPI、客户端与相关测试**；**不要**依赖本文件做机器可读路由表——**以路由注册代码为唯一真源**。

## 能力域地图（`/api/v1` 下）

- **认证**：访客与第三方登录等入站身份建立。
- **用户**：资料、设备、账号删除与内部列表（部分路径带 deprecated 语义，读代码注释）。
- **角色 / Agents**：搜索、推荐、创建、多媒体生成配置、OpenRouter 模型列表等 **C 端角色经济**。
- **聊天**：REST 完成式、**伴侣 WebSocket**、聊天内多媒体生成等。
- **会话 Chats**：历史消息、设置、投票、清会话等 **会话级运营**。
- **图片 / 通知 / 举报 / 设置 / 订阅**：对应子域的 CRUD 与后台入口。
- **语音列表**：可供客户端选择的音色等只读能力。
- **版本检查**：客户端上报 **App 版本码** 以驱动 **推送与功能门控**（字段名历史原因偏 Android，但语义是「端上版本」）。
- **角色主题**：打包展示一簇角色的运营配置。
- **实时语音 Live Chat**：状态轮询 + **独立 WS** 协议；细节见长文档 `docs/FR_LIVE_VOICE_CHAT.md`。
- **电话 Phone Calls**：外呼、入站 Twilio webhook、媒体流桥 **分属不同信任模型**；**仅用户显式给号 / 显式触发** 才允许外呼，禁止由隐式问候等自动拨号。

## WebSocket 提示

- WS **不会完整出现在 OpenAPI**；协议细节以 **专项设计文档 + `app/schemas` 中的帧模型** 为准。
