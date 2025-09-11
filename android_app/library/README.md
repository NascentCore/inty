# Library

## 快速开始

创建 Client 必须提供 API key，但是 CreateGuest 实际上接受空 API key。

```kotlin
client = ...().apiKey("")
client.createGuest()
```

## inty-sdk 总结

`inty-sdk` 包含 3 个核心子模块（及其他模块）

* `inty-kotlin-core` 提供核心 API 接口和模型
* `inty-kotlin-client-okhttp` 提供基于 OkHttp 的 HTTP 客户端实现
* `inty-kotlin` 作为主入口模块统一对外暴露

其他模块：

* `inty-kotlin-example` 空目录，stainless 自动生成，对项目无影响
* `inty-kotlin-lib` 空目录，stainless 生成中产生（不确定？）对项目无意义
* `inty-kotlin-proguard-test` 测试 ProGuard 和 R8 代码混淆兼容性的模块
  * 代码混淆测试：验证 SDK 在 ProGuard 和 R8 混淆后仍能正常工作
  * 序列化兼容性：测试 JSON 序列化/反序列化在混淆后是否正常
  * API 调用测试：确保客户端在混淆后能正常调用 API

## 核心模块关联和依赖关系

这三个模块构成了 Inty Kotlin SDK 的分层架构：

```ascii
inty-kotlin (主入口)
    └── inty-kotlin-client-okhttp (HTTP 客户端实现)
            └── inty-kotlin-core (核心 API 和模型)
```

1. **`inty-kotlin-core`** - 核心基础层
   * 定义 API 接口、数据模型、序列化逻辑
   * 提供 Jackson JSON 处理能力
   * 包含 HTTP 核心组件（Apache HttpClient）
   * 不依赖具体的 HTTP 客户端实现
2. **`inty-kotlin-client-okhttp`** - HTTP 客户端实现层
   * 依赖 `inty-kotlin-core` 获取核心接口
   * 基于 OkHttp 实现具体的 HTTP 请求
   * 提供日志拦截器等功能
3. **`inty-kotlin`** - 统一入口层
   * 依赖 `inty-kotlin-client-okhttp` 提供默认实现
   * 作为对外发布的主模块
   * 用户只需依赖此模块即可使用完整功能

* **分层解耦**：核心逻辑与 HTTP 实现分离
* **可扩展性**：未来可添加其他 HTTP 客户端实现
* **简化使用**：用户只需依赖主模块即可
