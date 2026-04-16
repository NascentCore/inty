# Workflows

## 发布内测轨道 AAB

运行[build_and_upload_android.yaml](https://github.com/NascentCore/inty-app/actions/workflows/build_and_upload_android.yaml)构建 release 变体，并上传 AAB 到 Google Play Internal Testing 轨道。

<img width="860" alt="image" src="https://github.com/user-attachments/assets/e3b5c920-3617-4f89-8f56-bfec0e62af2a" />

然后用 adspower 指纹浏览器打开[内测轨道](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/tracks/internal-testing)

<img width="860" alt="image" src="https://github.com/user-attachments/assets/abf30b54-311b-460c-a472-586cb25d85c6" />

<img width="860" alt="image" src="https://github.com/user-attachments/assets/a7956951-a72c-4832-b75a-fd32c0cc62c5" />

## Deployment model

<img width="300" height="582" alt="image" src="https://github.com/user-attachments/assets/21feb497-7c80-4601-b292-8134317c3c6e" />

Dev & prod sharing the same VM on GCP.

**iMate 第二 Inty 实例**：在 [build_and_deploy_backend.yml](build_and_deploy_backend.yml) / [build_and_deploy_ops.yml](build_and_deploy_ops.yml) 的 **Run workflow** 中选择 Environment `imate-dev`、`imate-prod` 或 **`imate`**（Ops 独立库与域名，见 [docs/OPS_IMATE_ENV_IMATE_RUNBOOK.md](../../docs/OPS_IMATE_ENV_IMATE_RUNBOOK.md)）；需对应 GitHub Environment `vars`（含 `OPS_SERVICE_PORT_ON_HOST`、`OPS_SERVICE_PUBLIC_URL` 等，见 `devops/README.md`）。

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
