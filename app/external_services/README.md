# external_services

## Cursor Summary

- 目录用途: 与外部服务（云与第三方）的直接适配层。
- 关键文件:
  - Google Cloud: `gcs.py`（存储）、`android_publisher.py`（Google Play Android Publisher）、`google_play_service.py`（Play 订阅/收据相关）。
  - Firebase: `firebase.py`（消息/通知等）。
  - `globals.py`: 统一外部资源/客户端的全局初始化或单例。
- 关联: 被 `app/services` 调用，为业务逻辑提供外部能力入口。
