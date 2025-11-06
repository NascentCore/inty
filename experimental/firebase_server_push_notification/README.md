# Firebase 服务器端推送示例

本示例展示如何在服务器端完成耗时任务后，通过 Firebase Cloud Messaging (FCM) 通知 Android 端拉取结果。代码位于 `experimental/firebase_server_push_notification` 目录下，包含：

- `backend/`：FastAPI 实现的示例后端。
- `android_app/`：最小可运行的 Android 应用工程，接入 Firebase 消息并向后端发起请求。

## 工作流程

1. Android 端启动后获取自身的 FCM `device_token`。
2. 用户点击按钮后，Android 端调用后端 `POST /process`，并将 `device_token` 一并提交。
3. 后端生成新的 `job_id`，异步执行耗时任务（示例中为 5 秒延迟，可自行调整为 300 秒），完成后写入内存结果存储。
4. 后端通过 Firebase Admin SDK，向对应 `device_token` 推送一条包含 `job_id` 的消息。
5. Android 端在 `FirebaseMessagingService` 中监听消息，收到后使用 `job_id` 调用后端 `GET /results/{job_id}` 拉取处理结果，并在界面上展示。

## 后端：FastAPI + Firebase Admin

### 环境准备

1. 前往 [Firebase 控制台](https://console.firebase.google.com/) 创建项目，启用 Cloud Messaging。
2. 在「项目设置」→「服务账号」下载 *Admin SDK 服务账号* 的 JSON 凭证，保存到本地，例如 `service-account.json`。
3. 将凭证路径设置到环境变量（两者任选其一）：

   ```bash
   export FIREBASE_SERVICE_ACCOUNT_FILE=/absolute/path/to/service-account.json
   # 或
   export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
   ```

4. 在目录 `backend/` 安装依赖并启动服务：

   ```bash
   cd experimental/firebase_server_push_notification/backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn backend.main:app --reload --port 8000
   ```

### 接口说明

- `POST /process`
  - 请求体：`{"device_token": "<FCM token>", "payload": {...}}`
  - 响应：`{"job_id": "<id>", "status": "pending"}`
  - 作用：登记新任务并异步执行长耗时处理；完成后自动向 `device_token` 推送结果通知。

- `GET /results/{job_id}`
  - 响应：`{"job_id": "<id>", "status": "finished", "result": {...}}`
  - 作用：供客户端轮询或在收到推送后获取具体结果。

> **提示**：示例中使用了最简单的内存存储，适合本地演示。在线环境可替换为 Redis、数据库等持久化方案，并通过消息队列、异步任务框架（如 Celery、RQ）处理真正的长任务。

## Android 应用

### 工程结构

示例工程位于 `android_app/`，核心文件：

- `MainActivity.kt`：获取 FCM Token，提交任务并监听结果。
- `ServerPushMessagingService.kt`：接收 FCM 推送，携带 `job_id` 拉取结果。
- `ResultFetcher.kt`：使用 OkHttp 调用后端接口。
- `activity_main.xml`：简单的按钮和状态文本展示界面。

### 集成步骤

1. 使用 Android Studio 导入 `android_app/` 目录。
2. 在 Firebase 控制台创建 Android 应用，`applicationId` 默认是 `com.example.fcmserverpush`，如有修改请同步更新 `app/build.gradle.kts`、`AndroidManifest.xml`。
3. 下载 `google-services.json` 放入 `android_app/app/src/main/`。
4. 确保 Android 端可以访问后端地址：
   - 在模拟器中，可保持 `ServerConfig.BASE_URL = "http://10.0.2.2:8000"`。
   - 真机调试时需改为电脑局域网 IP 或后端公网地址，同时注意防火墙与证书配置。
5. 运行应用，界面显示 FCM Token 后点击「提交任务」，待约 5 秒后即可在界面看到结果提示。

## 端到端验证

1. 启动后端：`uvicorn backend.main:app --reload --port 8000`
2. 打开 Android 应用，确保 Token 正常显示。
3. 点击按钮提交任务，观察后端日志会出现 `收到新任务`，随后 `完成处理`。
4. 大约 5 秒后，Android 界面更新为任务完成状态，同时 `Logcat` 中可以看到拉取结果的日志。

## 可拓展方向

- 使用数据库持久化任务状态，支持多进程或重启恢复。
- 借助 Celery、RQ、FastAPI BackgroundTask 等方式替换示例中的 `asyncio.sleep`。
- 在 FCM 数据消息中附带更多业务字段，如错误信息、进度百分比等。
- Android 端在通知栏显示推送信息，并跳转到详情页面。

## 注意事项

- `firebase-admin` 仅用于服务器环境，不应在客户端使用。
- 示例默认耗时 5 秒，实际业务可调整 `backend/main.py` 中的延迟或替换为真实计算。
- 若未正确配置服务账号或网络，后端会记录警告并跳过推送，可通过日志排查。
