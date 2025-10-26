＃ 数据

## 光标摘要

- 目录用途：负责数据获取与领域仓库，包装网络/本地持久化与业务实例。
- 区域关键：
  -`http/`: 网络层配置（`IntyNetworkManager`、`NetworkConfig`）、错误码与结果包装（`ApiResult`、`BusinessErrorCodes`）、服务接口（Auth/User/Chat/Agent/Subscription/Report 等）。
  -`api/model`:面向网络的DTO/VO与转换器（`ModelConverters`）。
  - `chat/` 与 `usecase/`: 会话管理与核心用例（发送消息、加载历史、同步数据等）。
  - `billing/`: 谷歌支付集成（价格/购买/状态/仓库/错误处理/本地存储）。
  - `store/`: 应用设置持久化（如 `IntySetting`）。
  - `di/`: 依赖注入模块（`ChatModule` 等）。
- 关联: 通过 `library/network` 与后端通信；与 `core/common`、`app` 层配合形成完整业务流。
