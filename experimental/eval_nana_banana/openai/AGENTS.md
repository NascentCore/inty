# `eval_nana_banana/openai/`：OpenAI Images Edit 离线评测

**一句话**：用 **官方 SDK 的 images.edit 路径** 对同一批失败 prompt 做 **多参考图编辑**；输出落在 `output_dir/openai/<model>/`，与 Fal 侧输出树 **隔离**。

## 心智

- **lib**：封装 `images.edit` 与 base64 解码落盘。
- **eval 脚本**：逐条 prompt；错误写入 `_error.json` 后继续。

## 认证

- `OPENAI_API_KEY`（常通过 `.env` + dotenv 加载）。
