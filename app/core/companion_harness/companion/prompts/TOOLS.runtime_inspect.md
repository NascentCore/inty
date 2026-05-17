# companion_runtime_inspect（DEBUG 运行时）

当用户询问**当前内部工作机制、模型与调用参数、真实注入的对话栈**等需要可核验的运行时事实时：

1. 调用 **`companion_runtime_inspect`**（参数可省略默认值）。
2. 阅读工具返回 JSON 中的 **`export_zip_repo_relative_path`**（或 `export_zip_absolute_path`）。
3. 用自然语言告诉用户该 **zip 文件路径**（便于在 REPL 工作目录下 `ls` / 解压查看）；zip 内含完整 `inspect_snapshot.json` 与 `manifest.json`。
4. 勿向用户朗读整份 JSON；可用摘要说明已打包调试数据。
