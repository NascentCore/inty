# Android Firebase Server Tasks Demo

该示例展示如何在服务端使用 Firebase Admin 通过 FCM 向 Android App 发送通知，以演示“服务器端任务完成时发送通知”的功能。

## 目录结构

- `fastapi_server.py` FastAPI 服务，提供 `/start_task` 启动“长任务”，任务完成后自动向设备推送通知；提供 `/notify` 直接推送接口。
- `firebase_client.py` Firebase Admin 初始化与消息发送封装。支持 `FIREBASE_CREDENTIALS_JSON` 或 `GOOGLE_APPLICATION_CREDENTIALS`。
- `tasks.py` 简单内存任务调度，模拟耗时任务并在完成时推送。
- `cli_send.py` 命令行工具，直接向 `device_token` 发送通知。
- `requirements.txt` 示例服务端依赖。
- `android_demo/` 安卓端示例 Kotlin 代码与 Gradle/Manifest 片段。

## 服务端运行

1. 准备服务账号凭据：
   - 方式A：将 JSON 内容放入环境变量 `FIREBASE_CREDENTIALS_JSON`
   - 方式B：设置 `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json`

2. 安装依赖并启动：

```bash
pip install -r experimental/android_firebase_server_tasks/requirements.txt
python -m experimental.android_firebase_server_tasks.fastapi_server
```

3. 启动任务并等待完成通知：

```bash
curl -X POST http://127.0.0.1:8080/start_task \
  -H 'Content-Type: application/json' \
  -d '{"device_token":"<YOUR_FCM_TOKEN>","task_name":"demo_task","duration_seconds":5}'
```

4. 直接发送测试通知：

```bash
python -m experimental.android_firebase_server_tasks.cli_send --token <YOUR_FCM_TOKEN> --data event=test key=value
```

## 安卓端集成

1. 在 Firebase 控制台创建 Android App 并下载 `google-services.json` 放入 `app/` 目录。
2. 参考 `android_demo/build_gradle_project.snippet.kts` 与 `android_demo/build_gradle_app.snippet.kts` 添加依赖与插件。
3. 在 `AndroidManifest.xml` 添加 `android_demo/AndroidManifest.snippet.xml` 中的 `service` 与权限。
4. 将 `android_demo/FCMService.kt`、`android_demo/NotificationChannels.kt` 放入你的模块源码包名下，`MainActivity.kt` 示例展示如何打印 Token。

## 注意
- Android 13+ 需要 `POST_NOTIFICATIONS` 权限并在运行时请求；示例为最简演示，未包含动态授权逻辑。
- 真实业务中，请在 App 获取到 token 后上传到你的服务端并绑定到用户。