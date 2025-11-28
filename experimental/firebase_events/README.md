<!-- CREATED_BY_AGENT -->
# Firebase Analytics 端到端极简 Demo

本示例以 `experimental/firebase_events` 为根，演示 Android 端上报 Firebase Analytics 事件、以及后端将导出的事件数据进行多维度聚合展示的完整流程。Demo 遵循 [Firebase Analytics 官方文档](https://firebase.google.com/docs/analytics) 中的事件、参数和维度命名约定，方便快速对照真实项目。

## 目录结构

- `android_demo/`：独立的 Android Studio 工程，包含按钮触发的典型事件（注册完成、开始关卡、内购等），会向 Firebase Analytics KTX SDK 上报多种参数和用户属性。
- `server/`：使用 FastAPI 的轻量服务，读取 `server/sample_data/events.json` 中模拟的 BigQuery 导出数据，并暴露聚合后的指标与维度拆分，同时提供一个静态页面展示结果。

## 快速开始

### 1. 运行 Android 端 Demo

1. 在 Firebase Console 创建 Android 应用，下载 `google-services.json` 并放入 `android_demo/app/google-services.json`。
2. 在 Android Studio 中打开 `android_demo` 目录，同步 Gradle 后即可安装运行。
3. 点击界面中的不同按钮会触发如下事件：
   - `tutorial_begin` / `level_up`: 携带 `level`, `character_id`, `engagement_time_msec` 等参数。
   - `sign_up`: 包含 `method`, `user_tier` 参数。
   - `in_app_purchase`: 附带 `value`, `currency`, `item_id`。
4. 在 DebugView 或 BigQuery 导出中即可看到这些事件，维度包括 `app_version`, `geo.country`, `device.category`, `screen_class` 等。

### 2. 启动数据展示服务

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

访问 <http://127.0.0.1:8000> 将看到：

- 事件概览表：展示事件计数、去重用户数、平均价值（若存在 `value` 参数）。
- 维度拆分：基于 `geo_country`、`device_category`、`app_version`、`screen_class` 计算 Top 3 维度组合。
- 参数快照：展示每个事件中最近一次上报的参数值，便于验证埋点是否完整。

### 3. 替换为真实数据（可选）

1. 将 BigQuery 导出的 `events_*` 表（或 Debug 模式导出的 JSON）转换为以下结构：
   ```json
   {
     "created_by": "CREATED_BY_AGENT",
     "events": [
       {
         "event_name": "tutorial_begin",
         "event_timestamp": "2024-11-20T08:00:00Z",
         "user_pseudo_id": "abc123",
         "device": {"category": "phone", "os_version": "34"},
         "geo": {"country": "US", "city": "Seattle"},
         "app": {"version": "1.3.0"},
         "screen_class": "MainActivity",
         "event_params": {"level": 1, "value": 4.99}
       }
     ]
   }
   ```
2. 覆盖 `server/sample_data/events.json` 后重新启动服务即可看到新的聚合结果。

## 注意事项

- Android 端 demo 未依赖 `android_app/` 下任何代码，可安全二次开发。
- 服务器端 demo 仅做可视化，未持久化数据；若需生产可扩展至 Cloud Functions、BigQuery 或 Looker Studio。
- 所有新建文件均标记 `CREATED_BY_AGENT` 以便审计。
