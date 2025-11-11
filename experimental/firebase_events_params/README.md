# Firebase 事件参数演示

本示例展示如何：

- 使用现有的 `app/core/config.py` 读取 Firebase 服务账号路径；
- 通过 GA4 Data API 查询指定事件的参数；
- 在 Android 端发送 `button_clicked` 事件并附带自定义参数，便于后续验证。

## 目录结构

```
experimental/firebase_events_params/
├── README.md
├── requirements.txt
├── fetch_button_clicked_params.py
└── android_demo/
    ├── build.gradle.kts
    ├── gradle.properties
    ├── settings.gradle.kts
    ├── google-services.json.example
    └── app/
        ├── build.gradle.kts
        └── src/main/
            ├── AndroidManifest.xml
            ├── java/com/example/firebaseeventsparams/MainActivity.kt
            ├── res/layout/activity_main.xml
            └── res/values/strings.xml
```

## Python：查询 `button_clicked` 事件参数

脚本 `fetch_button_clicked_params.py` 使用 `app.core.config` 中公用的配置对象来定位服务账号文件，并调用 GA4 Data API 查询事件参数。

### 1. 安装依赖

```bash
pip install -r experimental/firebase_events_params/requirements.txt
```

### 2. 准备配置

1. 确保根目录下的 `config.yaml` 中已配置 `firebase.service_account_path`；
2. 若路径为相对路径，请将服务账号 JSON 放置在指定位置；
3. 获取 Firebase 关联的 GA4 Property ID（形如 `123456789`），可在 Firebase 控制台 → Analytics → 管理 中查看。

### 3. 运行脚本

```bash
python experimental/firebase_events_params/fetch_button_clicked_params.py \
  --property-id 123456789 \
  --event-name button_clicked \
  --limit 20
```

运行结果会列出事件参数名称、示例值与计数。如需仅测试配置，可使用 `--dry-run` 查看解析出的服务账号路径而不访问 API。

## Android：发送带参数的事件

`android_demo` 提供一个最小化的 Kotlin 应用，内含一个按钮。点击后会：

1. 调用 `FirebaseAnalytics` 记录 `button_clicked` 事件；
2. 附带一组演示参数（如按钮标签、点击来源、测试标记）；
3. 将同一组参数显示在界面上，便于快速确认。

### 1. 准备工程

1. 在 Firebase 控制台添加包名为 `com.example.firebaseeventsparams` 的 Android 应用；
2. 下载生成的 `google-services.json` 并覆盖到 `android_demo/app/google-services.json`（可复制示例文件改名）。

### 2. 使用 Android Studio 构建

1. 打开 `experimental/firebase_events_params/android_demo`；
2. 同步 Gradle；
3. 连接真机或启动模拟器后运行应用；
4. 进入 Firebase 控制台 → Analytics → 实时 → 事件，以验证 `button_clicked` 是否收到。

### 3. 调整参数

在 `MainActivity.kt` 的 `buildDemoParams()` 方法中可以自由增删参数；更新后重新运行即可。若需要与后端脚本联动，请确保事件名与参数键名保持一致。

## 后续扩展思路

- 为脚本增加 BigQuery 导出或批量查询能力；
- 在 Android 端展示最近一次事件的发送状态（例如通过 DebugView）；
- 接入后台任务定期拉取事件参数并写入内部可观测性系统。
