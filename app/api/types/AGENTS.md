# `app/api/types/`：API 层共享类型（非全量 DTO）

**一句话**：放 **HTTP 层与内部模块都要引用的少量共享类型**（例如 **LLMConfig**）；**大面积请求/响应体** 仍在 `app/schemas`。

## 心智

- **LLMConfig**：描述「一次模型调用可读到的参数视图」；**不包含** 已废弃的每请求 API key / base_url——全局客户端由配置统一托管。
- **新增类型前**：先问自己「是否跨越多个包被引用」；否则 closer to call site 定义即可。
