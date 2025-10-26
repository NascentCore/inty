＃ 图书馆

## 快速开始

创建Client必须提供API key，但是CreateGuest则接受空API key。```kotlin
client = ...().apiKey("")
client.createGuest()
```## inty-sdk 总结`inty-sdk` 包含 3 个核心子模块（及其他模块）

- `inty-kotlin-core` 提供核心 API 接口和模型
- `inty-kotlin-client-okhttp`提供基于 OkHttp 的 HTTP 客户端实现
-`inty-kotlin` 作为主入口模块统一对外暴露

其他模块：

- `inty-kotlin-example`空目录，不锈钢自动生成，对项目无影响
-`inty-kotlin-lib`空目录，不锈钢生成中产生（免费？）对项目无意义
-`inty-kotlin-proguard-test`测试ProGuard和R8代码兼容性兼容的模块
  - 代码混乱测试：验证 SDK 在 ProGuard 和 R8 混乱后仍能正常工作
  - 序列化兼容性：测试JSON序列化/反序列化在冲突后是否正常
  - API 调用测试：确保客户端在干扰后能正常调用 API

## 核心模块关联和依赖关系

这三个模块构成了 Inty Kotlin SDK 的分层架构：```ascii
inty-kotlin (主入口)
    └── inty-kotlin-client-okhttp (HTTP 客户端实现)
            └── inty-kotlin-core (核心 API 和模型)
```

1. **`inty-kotlin-core`** - 核心基础层
   - 定义API接口、数据模型、序列化逻辑
   - 提供 Jackson JSON 处理能力
   - 包含HTTP核心组件（Apache HttpClient）
   - 不依赖具体的HTTP客户端实现
1.**`inty-kotlin-client-okhttp`** - HTTP 客户端实现层
   - 依赖 `inty-kotlin-core`获取核心接口
   - 基于OkHttp实现具体的HTTP请求
   - 提供日志拦截器等功能
1.**`inty-kotlin`** - 统一入口层
   - 依赖 `inty-kotlin-client-okhttp`提供默认实现
   -作为对外发布的主要模块
   - 用户只需依赖此模块即可使用完整功能

- **分层解耦**：核心逻辑与HTTP实现分离
- **可扩展性**：未来可添加其他HTTP客户端实现
- **简化使用**：用户只需依赖主模块即可

## Cursor 摘要

- 目录用途: 聚合可复用的独立库模块。
- 当前子模块:
  -`network`: 提供 HTTP 调用的响应包装与适配（如 `HttpResponseCallAdapterFactory`、`HttpResponseCall`）。
  - `utils`: 图片压缩、网络工具等通用能力（如 `ImageCompressManager`/`ImageCompressUtils`、`NetworkUtils`）。
- 说明: 文档中提到的 `inty-sdk` 为可选的 SDK 子模块内容；本仓库实际以 `network` 与 `utils` 两个模块为主，支撑 App 网络与工具层能力。
