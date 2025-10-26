# network

## Cursor Summary

- 目录用途: 提供网络层基础能力与响应包装。
- 关键文件:
  - `core/HttpResponseCallAdapterFactory`、`core/HttpResponseCall`: 自定义 Call 与适配器，将响应统一包装为结果类型。
  - `core/HttpResult`、`core/MoshiResultTypeAdapterFactory`: 结果数据结构与 Moshi 类型处理。
  - `utils/MoshiUtils`: Moshi 工具与配置扩展。
  - `error/BusinessException`、`error/GlobalErrorHandler`: 业务异常定义与全局错误处理。
- 关联: 供 `core/data` 中的 `IntyNetworkManager` 与各服务接口使用，实现稳定可靠的 API 调用。
