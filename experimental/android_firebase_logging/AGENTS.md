# `android_firebase_logging/`：Firebase 观测示例 App

**一句话**：最小 Android 样例，演示 **Analytics + Crashlytics + Performance** 三类 Firebase 观测如何接入；用于 **抄作业式集成参考**，不是产品 App。

## 读者

- 需要理解「事件、崩溃、性能 trace 如何统一走一个 LoggingManager」的 Android 工程师。

## 原则

- **不把 `google-services.json` 提交到公共仓库**；示例用 `*.example` 占位。
- **Kotlin + Material Views**；最低/目标 SDK 以 Gradle 为准。
- **扩展方向**（Remote Config、FCM 等）仅列在概念层——实现以 README 与源码为准。

## 深入阅读

- 逐步集成：[`FIREBASE_SETUP_GUIDE.md`](FIREBASE_SETUP_GUIDE.md) 与 [`README.md`](README.md)。
