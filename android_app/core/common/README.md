# common

## Cursor Summary

- 目录用途: 提供应用通用的基础能力与封装。
- 关键文件:
  - `base/`: `BaseActivity`、`BaseVM` 等基础基类。
  - `analytics/`: `AnalyticsMixin`、`GlobalExceptionHandler`、`PageTrackingHelper` 等埋点/异常处理。
  - `event/`: 事件发布/订阅模型与 `EventBus`。
  - `startup/`: 启动期资源预加载（`ImagePreloadManager`）。
  - `ui/IntelliWebView`: 内嵌 WebView 能力封装。
  - `utils/`: 工具集合，如 `HeartAppUtils`、`TextParser`。
- 作用: 为上层 `app` 与其他模块提供稳定、可复用的通用基建。
