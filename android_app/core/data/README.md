# data - 数据层

## Cursor Summary

- 目录用途: 负责数据获取与领域仓库，封装网络/本地持久化与业务用例，现已落地 Room Offline-First。
- 关键区域:
  - `api/`: Retrofit API 接口与 `HttpResult` 调用路径（统一单网络栈）。
  - `http/`: 网络基础设施（`NetworkConfig`、`NetworkStateManager`、统一请求配置）。
  - `api/model`: 面向网络的本地 DTO/VO 类型定义。
  - `chat/` 与 `usecase/`: 会话管理与核心用例（发送消息、加载历史、同步数据等）。
  - `chat/local/db`: Room schema（`IntyChatDatabase`、`ChatMessageEntity`、`ChatSyncStateEntity`）与离线缓存映射，所有 UI 读取均来自本地数据库。
  - `billing/`: 谷歌支付集成（价格/购买/状态/仓库/错误处理/本地存储）。
  - `store/`: 应用设置持久化（如 `IntySetting`），详见 [MMKV_USAGE.md](./MMKV_USAGE.md)。
  - `di/`: 依赖注入模块（`ChatModule` 等）。
- 关联: 通过 `library/network` 与后端通信；与 `core/common`、`app` 层配合形成完整业务流。
