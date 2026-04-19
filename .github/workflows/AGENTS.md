# Workflows

- IntelliMate已经进入维护状态（maintenance mode），不应该再进行改动

## 发布内测轨道 AAB

运行[build_and_upload_android.yaml](https://github.com/NascentCore/inty-app/actions/workflows/build_and_upload_android.yaml)构建 release 变体，并上传 AAB 到 Google Play Internal Testing 轨道。

<img width="860" alt="image" src="https://github.com/user-attachments/assets/e3b5c920-3617-4f89-8f56-bfec0e62af2a" />

然后用 adspower 指纹浏览器打开[内测轨道](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/tracks/internal-testing)

## iMate Android CI（编译）

变更 [`imate_android_app/`](/imate_android_app/) 或 [ci_imate_android_app.yaml](ci_imate_android_app.yaml) 时触发：在 `android-builder` 上执行 `./gradlew :app:assembleDebug`，作为合并前编译检查。

## iMate 发布内测轨道 AAB

运行 [build_and_upload_imate_android.yaml](https://github.com/NascentCore/inty-app/actions/workflows/build_and_upload_imate_android.yaml) 在 [`imate_android_app/`](/imate_android_app/) 构建 `bundleRelease`，将 AAB 上传到 **Google Play Internal testing**（`packageName`: `com.inty.imate`）。定时默认每日 **UTC 02:30**（北京时间 10:30），也可手动 **Run workflow**。

**Secrets**：默认使用 `GCP_SERVICE_ACCOUNT_KEY_GPLAY_UPLOAD`（与 IntelliMate 同名）。须满足其一：

- 同一服务账号在 Play Console「API 访问」中已对应用 **com.inty.imate** 授权上传；或
- 另存一份仅用于 iMate 的 JSON，命名为仓库 Secret（例如 `GCP_SERVICE_ACCOUNT_KEY_GPLAY_UPLOAD_IMATE`），并修改 [build_and_upload_imate_android.yaml](build_and_upload_imate_android.yaml) 中 `upload-google-play` 步骤的 `serviceAccountJsonPlainText` 引用。

**构建前提（CI 与本地一致）**：`imate_android_app/sign/imate.jks` 与 `signing-config.json` 须在检出后的工作区中存在（通常已纳入仓库或由内部流程注入），否则 Gradle 配置阶段会失败。

在 Play Console 打开 **com.inty.imate** 对应应用的 **Internal testing** 轨道查看版本（URL 随开发者账号与应用 ID 变化，以控制台为准）。

<img width="860" alt="image" src="https://github.com/user-attachments/assets/abf30b54-311b-460c-a472-586cb25d85c6" />

<img width="860" alt="image" src="https://github.com/user-attachments/assets/a7956951-a72c-4832-b75a-fd32c0cc62c5" />

## Deployment model

<img width="300" height="582" alt="image" src="https://github.com/user-attachments/assets/21feb497-7c80-4601-b292-8134317c3c6e" />

Dev & prod sharing the same VM on GCP.

**iMate 第二 Inty 实例**：[build_and_deploy_backend.yml](build_and_deploy_backend.yml)：`main` **push** 默认 **`imate-dev`**（`config.yaml.imate_dev`）；**schedule** 默认 GitHub Environment **`imate-prod`**（`config.yaml.imate_prod`）。容器名统一由当前 **Environment 变量 `INTY_BACKEND_CONTAINER_NAME`**（`vars.INTY_BACKEND_CONTAINER_NAME`）决定，各 Environment（如 `dev`、`prod`、`imate-dev`、`imate-prod`）分别配置。手动 **Run workflow** 默认 `imate-dev`。与 [build_and_deploy_ops.yml](build_and_deploy_ops.yml) 一样可选 `imate-dev` / `imate-prod` / **`imate`**（Ops 见 [docs/OPS_IMATE_ENV_IMATE_RUNBOOK.md](../../docs/OPS_IMATE_ENV_IMATE_RUNBOOK.md)）；还需 `SERVICE_PORT_ON_HOST`、`SERVICE_PUBLIC_URL` 等（见 `devops/README.md`）。

## Dify 定时聊天调用

运行 [dify_chat_cron.yaml](https://github.com/NascentCore/inty-app/actions/workflows/dify_chat_cron.yaml) 定时调用 Dify API。

### 配置要求

- 需要在 GitHub Repository Secrets 中配置 `DIFY_API_KEY`
- 默认每日 UTC 00:00 自动执行
- 支持手动触发（通过 Actions 页面的 "Run workflow" 按钮）

### 验证方式

1. 进入 [Actions 页面](https://github.com/NascentCore/inty-app/actions)
2. 点击 "Dify 定时聊天调用" workflow
3. 点击 "Run workflow" 手动触发
4. 查看执行日志，确认 API 调用成功（状态码 200）

## 用户数据分析日报周报兜底任务

运行 [user_analytics_report_fallback.yaml](https://github.com/NascentCore/inty-app/actions/workflows/user_analytics_report_fallback.yaml) 作为 `push_worker` 之外的兜底入口：

- **不替换主链路**：日报/周报主任务仍由 `push_worker` 定时执行。
- **自动兜底**：
  - 每日 UTC 08:00 自动补算 `T-1` 日报
  - 每周一 UTC 09:00 自动补算上一周周报（周一日期）
- **手动重算**：支持 `workflow_dispatch` 传入 `report_type`、`report_date`，并可用 `force=true` 覆盖重算。
