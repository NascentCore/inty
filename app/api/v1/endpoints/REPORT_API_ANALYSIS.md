# Report API 端点请求和响应类型分析

## 端点概览

Report API 包含以下端点：

1. **POST `/api/v1/report/`** - 创建举报/反馈（主要端点）

**注意**：图片上传请使用通用的 `/api/v1/images` 端点。

---

## 1. POST `/api/v1/report/` - 创建举报/反馈

### 请求类型：`ReportCreate`

定义见 ```26:50:app/schemas/report.py```

#### 字段说明

各字段的详细说明见 ```30:51:app/schemas/report.py``` 中的 `Field` description。

关键点：
- **target_id**: Report 模式需提供有效对象ID，Feedback 模式可为空字符串
- **target_type**: `"USER"` 或 `"AGENT"`，Feedback 模式通常使用 `"USER"`
- **reason_codes** (推荐): 原因代码列表，详见下方映射表。如果未提供，可从 `reason_ids` 自动转换
- **reason_ids** (已废弃): 原因ID列表，后端会根据 `report_type` 自动转换为 `reason_codes`，转换逻辑见 ```40:58:app/services/report_service.py```
- **report_type**: `"REPORT"`（默认）或 `"FEEDBACK"`

#### 请求示例

**创建举报：**
```json
{
  "target_id": "agent_123",
  "target_type": "AGENT",
  "reason_codes": ["SENSITIVE_CONTENT", "MISINFORMATION"],
  "description": "This agent contains inappropriate content",
  "image_urls": ["https://example.com/image1.jpg"],
  "report_type": "REPORT"
}
```

**创建反馈：**
```json
{
  "target_id": "",
  "target_type": "USER",
  "reason_codes": ["CHAT_NOT_NATURAL", "UI_INCONVENIENT"],
  "description": "The app feels slow and UI is confusing",
  "image_urls": [],
  "report_type": "FEEDBACK"
}
```

### 响应类型：`APIResponse[None]`

定义见 ```28:43:app/schemas/response.py```

#### 成功响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

#### 错误响应示例

```json
{
  "code": 400,
  "message": "Invalid reason_ids: [99]. These reason IDs do not exist.",
  "data": null
}
```

---

## 原因代码映射

原因代码映射定义在 `app/models/report.py` 中：

- **Report 原因代码映射**：见 `REASON_ID_TO_CODE` (```14:21:app/models/report.py```)
- **Feedback 原因代码映射**：见 `FEEDBACK_REASON_ID_TO_CODE` (```26:34:app/models/report.py```)

Android 端的对应关系定义在 `android_app/app/src/main/kotlin/com/ai/intellimate/agent/report/ReportViewModel.kt`：
- **Report reasons**：见 `_reportReasons` (```45:72:android_app/app/src/main/kotlin/com/ai/intellimate/agent/report/ReportViewModel.kt```)
- **Feedback reasons**：见 `_feedbackReasons` (```76:111:android_app/app/src/main/kotlin/com/ai/intellimate/agent/report/ReportViewModel.kt```)

---

## 验证规则与注意事项

验证逻辑实现见 ```30:66:app/services/report_service.py``` (`create_report` 函数)：

1. **必填字段**：`target_id`（Feedback 模式可为空字符串）、`target_type`
2. **原因验证**：必须提供 `reason_codes` 或 `reason_ids` 中的至少一个，且包含至少一个非空值（见 ```62:66:app/services/report_service.py```）
3. **类型转换**：如果只提供 `reason_ids`，后端会根据 `report_type` 自动转换为 `reason_codes`（见 ```40:58:app/services/report_service.py```）
4. **Feedback 模式**：`target_id` 可为空字符串，`target_type` 通常为 `"USER"`，必须设置 `report_type: "FEEDBACK"`
5. **图片上传**：使用 `/api/v1/images` 端点上传，获取 URL 后放入 `image_urls` 字段
6. **权限要求**：创建需要已登录用户（见 ```90:90:app/api/v1/endpoints/report.py```）
