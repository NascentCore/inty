# library - 库模块

## 快速开始

创建 Client 必须提供 API key，但是 CreateGuest 实际上接受空 API key。

```kotlin
client = ...().apiKey("")
client.createGuest()
```

## Cursor Summary

- 目录用途: 聚合可复用的独立库模块。
- 当前子模块:
  - `network`: 提供 HTTP 调用的响应包装与适配（如 `HttpResponseCallAdapterFactory`、`HttpResponseCall`）。
  - `utils`: 图片压缩、网络工具等通用能力（如 `ImageCompressManager`/`ImageCompressUtils`、`NetworkUtils`）。
- 说明: 文档中提到的 `inty-sdk` 为可选的 SDK 子模块内容；本仓库实际以 `network` 与 `utils` 两个模块为主，支撑 App 网络与工具层能力。
