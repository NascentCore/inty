# Chat Completions 业务动作（business_actions）接口测试步骤

## 说明

`ChatCompletionsBizActionsApiTest` 为集成测试，会请求本地后端 `http://localhost:8000`，验证 chat completions 返回的 `business_actions` 非空且结构正确。CI 不启动后端，因此该测试在 CI 中会被跳过（需设置环境变量才执行）。

## 运行方式

1. 启动本地测试后端（例如：`cp devops/config.yaml.test config.yaml && backend/inty/start.sh --test`，确保监听 8000 端口）。
2. 在 `android_app` 目录下执行：

   ```bash
   RUN_LOCALHOST_CHAT_COMPLETIONS_TEST=true ./gradlew :core:data:testDebugUnitTest --tests "ai.sxwl.android.data.api.ChatCompletionsBizActionsApiTest"
   ```

不设置 `RUN_LOCALHOST_CHAT_COMPLETIONS_TEST=true` 时，该测试会被跳过，不会失败。
