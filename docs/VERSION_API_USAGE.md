# 版本检查 API 用法

版本检查 API 允许客户端验证是否需要更新到 Google Play 商店上提供的最新版本。

## 端点

### POST /api/v1/版本/检查

检查客户端应用程序是否需要更新。**请求正文：**```json
{
  "version": "1.2.3",
  "platform": "android"
}
```**回复：**```json
{
  "code": 200,
  "success": true,
  "message": "Success",
  "data": {
    "current_version": "1.2.3",
    "latest_version": "1.3.0",
    "latest_version_code": 130,
    "update_required": true,
    "force_update": false,
    "minimum_version": "1.0.0",
    "changelog": "Bug fixes and performance improvements",
    "download_url": "https://play.google.com/store/apps/details?id=com.ai.inty",
    "message": "Update available"
  }
}
```### 获取/api/v1/版本/最新

获取最新版本信息（仅限管理员）。**回复：**```json
{
  "code": 200,
  "success": true,
  "message": "Success",
  "data": {
    "version_code": 130,
    "version_name": "1.3.0",
    "status": "completed",
    "release_notes": "Bug fixes and performance improvements",
    "user_fraction": null
  }
}
```＃＃ 配置

添加以下设置`config.yaml`:

```yaml
google_play:
  package_name: com.ai.intellimate
  service_account_key: inty-backend-key.json
  enable_version_check: true
  min_supported_version: "1.0.0"
  force_update_versions: ["1.0.5", "1.1.2"] # Versions that require force update
  release_track: internal # Track to query: internal/closed/open/production
  fallback_tracks: [production, internal] # Fallback tracks if primary fails
```### 轨道配置

- **release_track**: Primary track 用于查询版本信息
  -`internal`：内部测试轨道（最多100名测试人员）
  -`closed`：封闭测试轨道（仅限受邀团体）
  -`open`：开放测试轨道（公测）
  -`production`：Production 曲目（对所有用户直播）

- **fallback_tracks**：如果 primary 轨道没有版本，则要尝试的轨道数组
  - 在曲目之间转换时很有用
  - 系统将按顺序尝试曲目，直到找到版本信息

### 版本名称解析

系统自动处理来自 Google Play 的复杂版本名称格式：

-`"217 (1.0.1 (507a57a))"`→ 摘录`"1.0.1"`
- `"(1.0.1)"`→ 摘录`"1.0.1"`
- `"1.0.1"`→ 按原样使用
-`"v1.2.3"`→ 按原样使用

无论 Google Play 的内部命名约定如何，这都可以确保准确的版本比较。## 响应字段

-`update_required`: 是否有更新
-`force_update`：是否强制更新
-`minimum_version`：最低支持版本（低于此需要强制更新）
-`changelog`：Google Play 管理中心的发行说明
-`download_url`：直接链接到 Play 商店中的应用程序

## 错误处理

如果 Google Play API 不可用，该服务将返回一个安全响应，允许应用程序继续运行：```json
{
  "current_version": "1.2.3",
  "latest_version": "unknown",
  "update_required": false,
  "force_update": false,
  "message": "Version check failed but app can continue",
  "error": "API connection failed"
}
```## 客户端实现示例```typescript
async function checkForUpdates() {
  try {
    const response = await fetch("/api/v1/version/check", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        version: "1.2.3",
        platform: "android",
      }),
    });

    const result = await response.json();
    const versionData = result.data;

    if (versionData.force_update) {
      // Show mandatory update dialog
      showForceUpdateDialog(versionData);
    } else if (versionData.update_required) {
      // Show optional update prompt
      showUpdatePrompt(versionData);
    }
  } catch (error) {
    console.log("Version check failed, continuing normally");
  }
}
```
