# 单角色图片打标 only_include_ai_character — 测试步骤

用于将「仅含一个角色」的聊天生图打上 `only_include_ai_character=True`，使其可作为生图失败时的兜底候选。以下步骤在仓库根目录、且 `export PYTHONPATH=.` 下执行。

## 1. 单张图试跑并验证

### 1.1 打标单张图

```bash
python scripts/chat_image_gen_fallbacks_only_include_ai_character/tag_only_include_ai_character_from_json.py \
  --chat-images-json only-include-imate.json \
  --config devops/config.yaml.prod \
  --limit 1
```

（非 dry-run 时会提示确认，输入 `y` 继续。）

**预期**：日志中出现 1 条 `updated`，且无报错。

### 1.2 核对 DB

对日志中出现的 GCS URI（或 JSON 里该条目的 `image_url` 转成 `gs://...`）执行：

```sql
SELECT url, resource_metadata->>'only_include_ai_character'
FROM resources
WHERE url = 'gs://inty-static/chat_images/...';
```

**预期**：`only_include_ai_character` 为 `true`。

### 1.3 手动检查兜底查询

用上一步的 GCS URI 跑验证脚本，确认该图会出现在 `get_generated_images_for_agent(..., only_include_ai_character=True)` 的结果中（此步骤不在 CI 中执行）：

```bash
python scripts/chat_image_gen_fallbacks_only_include_ai_character/verify_only_include_ai_character_fallback.py \
  --gcs-uri "gs://inty-static/chat_images/AGENT_ID/filename.jpg" \
  --config devops/config.yaml.prod
```

**预期**：输出 `OK: ... is in get_generated_images_for_agent(..., only_include_ai_character=True)`，退出码 0。

## 2. 全量打标

确认单张图行为正确后，对全部 `one_character=true` 条目打标：

```bash
python scripts/chat_image_gen_fallbacks_only_include_ai_character/tag_only_include_ai_character_from_json.py \
  --chat-images-json only-include-imate.json \
  --config devops/config.yaml.prod \
  --yes
```

**可选**：先做一次 dry-run 查看将要更新的数量与 URI：

```bash
python scripts/chat_image_gen_fallbacks_only_include_ai_character/tag_only_include_ai_character_from_json.py \
  --chat-images-json only-include-imate.json \
  --config devops/config.yaml.prod \
  --dry-run
```
