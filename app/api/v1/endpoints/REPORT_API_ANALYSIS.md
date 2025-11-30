# Report API 端点请求和响应类型分析

## 端点概览

Report API 包含以下端点：

1. **POST `/api/v1/report/`** - 创建举报/反馈（主要端点）
2. **GET `/api/v1/report/`** - 查询举报记录列表（已废弃，仅内部使用）

**注意**：图片上传请使用通用的 `/api/v1/images` 端点，而不是已废弃的 `/api/v1/report/upload-image`。

---

## 1. POST `/api/v1/report/` - 创建举报/反馈

### 请求类型：`ReportCreate`

```python
class ReportCreate(BaseModel):
    target_id: str                    # 必填：被举报对象ID（feedback 模式下可为空字符串）
    target_type: TargetType           # 必填：被举报对象类型（USER 或 AGENT）
    reason_ids: Optional[List[int]]   # 可选：原因ID列表（已废弃，使用 reason_codes）
    reason_codes: Optional[List[str]]  # 可选：原因代码列表（推荐使用）
    image_urls: Optional[List[str]]   # 可选：图片URL列表，默认 []
    description: Optional[str]         # 可选：描述信息
    request_id: Optional[str]         # 可选：请求ID（用于追踪）
    report_type: Optional[ReportType] # 可选：记录类型（REPORT 或 FEEDBACK），默认为 REPORT
```

#### 字段说明

- **target_id**: Report 模式需提供有效对象ID，Feedback 模式可为空字符串
- **target_type**: `"USER"` 或 `"AGENT"`，Feedback 模式通常使用 `"USER"`
- **reason_codes** (推荐): 原因代码列表，详见下方映射表。如果未提供，可从 `reason_ids` 自动转换
- **reason_ids** (已废弃): 原因ID列表，后端会根据 `report_type` 自动转换为 `reason_codes`
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

```python
class APIResponse(BaseModel, Generic[T]):
    code: int = 200              # HTTP 状态码
    message: str = "success"     # 响应消息
    data: Optional[T] = None     # 响应数据（创建成功时为 None）
```

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

## 2. GET `/api/v1/report/` - 查询举报记录（已废弃，仅内部使用）

### 请求参数（Query Parameters）

```python
reason_ids: Optional[List[int]] = None      # 已废弃：使用 reason_codes
reason_codes: Optional[List[str]] = None    # 原因代码列表
target_id: Optional[str] = None             # 被举报对象ID
target_type: Optional[TargetType] = None   # 被举报对象类型
status: Optional[ReportStatus] = None       # 状态（PENDING, PROCESSING, RESOLVED, REJECTED）
reporter_id: Optional[str] = None           # 举报人ID
report_type: Optional[ReportType] = None   # 记录类型（REPORT 或 FEEDBACK）
page: int = 1                                # 页码，默认 1
page_size: int = 20                          # 每页数量，默认 20
```

**注意**：此端点需要管理员权限（`is_superuser`）

### 响应类型：`APIResponse[PaginationData[ReportOut]]`

```python
class PaginationData(BaseModel, Generic[T]):
    list: List[T] = []         # 数据列表
    total: int = 0             # 总记录数
    page: int = 1              # 当前页码
    page_size: int = 10        # 每页数量
    total_pages: int = 0       # 总页数

class ReportOut(BaseModel):
    id: str                    # 举报记录ID
    target_id: str             # 被举报对象ID
    target_type: str           # 被举报对象类型
    reporter_id: str           # 举报人ID
    reason_ids: List[int]      # 已废弃：原因ID列表
    reason_codes: List[str]    # 原因代码列表
    image_urls: List[str]      # 图片URL列表
    description: Optional[str] # 描述信息
    status: str                # 状态（PENDING, PROCESSING, RESOLVED, REJECTED）
    report_type: Optional[str] # 记录类型（REPORT 或 FEEDBACK，None 视为 REPORT）
    created_at: datetime       # 创建时间
```

#### 成功响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "id": "report_123",
        "target_id": "agent_456",
        "target_type": "AGENT",
        "reporter_id": "user_789",
        "reason_ids": [1, 2],
        "reason_codes": ["SENSITIVE_CONTENT", "MISINFORMATION"],
        "image_urls": ["https://example.com/image1.jpg"],
        "description": "Inappropriate content",
        "status": "PENDING",
        "report_type": "REPORT",
        "created_at": "2024-01-01T12:00:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
}
```

#### 错误响应示例

```json
{
  "code": 400,
  "message": "Unauthorized access",
  "data": null
}
```

---

## 原因代码映射

### Report 原因代码

| ID | Code | 描述 |
|---|---|---|
| 1 | `SENSITIVE_CONTENT` | Sensitive or sexual content |
| 2 | `MISINFORMATION` | Misinformation |
| 3 | `FRAUD_SCAMS` | Fraud or scams |
| 4 | `PRIVACY_VIOLATION` | Violation of privacy |
| 5 | `HARMFUL_MINORS` | Harmful to minors |
| 6 | `IP_VIOLATION` | Violations of my intellectual property |

### Feedback 原因代码

| ID | Code | 描述 |
|---|---|---|
| 0 | `OTHER` | Other, please describe below |
| 1 | `CHAT_NOT_NATURAL` | Chat replies don't feel natural / off-topic |
| 2 | `CHARACTER_MISMATCH` | The character doesn't match its persona |
| 3 | `APP_SLOW` | The app is slow or gets stuck |
| 4 | `FEATURE_HARD_TO_FIND` | I couldn't find / how to use this feature |
| 5 | `UI_INCONVENIENT` | UI or interaction feels inconvenient |
| 6 | `NEW_FEATURE` | I'd like to see a new feature or improvement |

---

## 验证规则与注意事项

1. **必填字段**：`target_id`（Feedback 模式可为空字符串）、`target_type`
2. **原因验证**：必须提供 `reason_codes` 或 `reason_ids` 中的至少一个，且包含至少一个非空值
3. **类型转换**：如果只提供 `reason_ids`，后端会根据 `report_type` 自动转换为 `reason_codes`
4. **Feedback 模式**：`target_id` 可为空字符串，`target_type` 通常为 `"USER"`，必须设置 `report_type: "FEEDBACK"`
5. **图片上传**：使用 `/api/v1/images` 端点上传，获取 URL 后放入 `image_urls` 字段
6. **权限要求**：创建需要已登录用户，查询列表需要管理员权限（`is_superuser`）

