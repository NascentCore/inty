# FCM 服务端调试指南

## 概述

本指南介绍在 app 开发未就绪的情况下，如何在服务端调试 Firebase Cloud Messaging (FCM) 集成。

## 调试方法

### 方法 1: Dry Run 模式（推荐）

Dry Run 模式会验证消息格式和配置，但不会实际发送消息到设备。这是最安全的测试方法。

#### 使用测试脚本

```bash
# 测试单个 token（dry run 模式，默认）
python tools/scripts/fcm/test_fcm_push.py --token YOUR_FCM_TOKEN --dry-run

# 测试用户 ID（从数据库获取 token）
python tools/scripts/fcm/test_fcm_push.py --user-id USER_ID --dry-run

# 测试推送服务
python tools/scripts/fcm/test_fcm_push.py --test-push-service --user-id USER_ID --dry-run
```

#### 在代码中使用

```python
from app.services import notification_service

# Dry run 模式
success = await notification_service.send_fcm_multicast(
    db=db,
    user_ids=[user_id],
    title="测试标题",
    body="测试内容",
    dry_run=True,  # 启用 dry run
)
```

#### Dry Run 模式特点

- ✅ 验证消息格式是否正确
- ✅ 验证 Firebase 配置是否正确
- ✅ 验证 token 格式是否有效
- ✅ 不会实际发送消息
- ✅ 不会产生费用
- ✅ 不会打扰用户

### 方法 2: 使用测试脚本

测试脚本 `tools/scripts/fcm/test_fcm_push.py` 提供了多种测试方式：

#### 基本用法

```bash
# 1. 测试单个 token（dry run）
python tools/scripts/fcm/test_fcm_push.py --token YOUR_FCM_TOKEN

# 2. 测试单个 token（真实发送）
python tools/scripts/fcm/test_fcm_push.py --token YOUR_FCM_TOKEN --real

# 3. 测试用户 ID
python tools/scripts/fcm/test_fcm_push.py --user-id USER_ID

# 4. 测试推送服务
python tools/scripts/fcm/test_fcm_push.py --test-push-service --user-id USER_ID
```

#### 高级用法

```bash
# 自定义标题和内容
python tools/scripts/fcm/test_fcm_push.py \
    --token YOUR_FCM_TOKEN \
    --title "自定义标题" \
    --body "自定义内容" \
    --dry-run

# 添加图片
python tools/scripts/fcm/test_fcm_push.py \
    --token YOUR_FCM_TOKEN \
    --image-url "https://example.com/image.jpg" \
    --dry-run

# 添加数据字段
python tools/scripts/fcm/test_fcm_push.py \
    --token YOUR_FCM_TOKEN \
    --data '{"chat_id":"123","type":"test"}' \
    --dry-run
```

#### 获取测试 Token

1. **从 Firebase Console 获取**：

   - 登录 Firebase Console
   - 进入项目设置 > Cloud Messaging
   - 查看或生成测试 token

2. **从数据库获取**：

   ```sql
   SELECT token, user_id, created_at
   FROM device_tokens
   WHERE user_id = 'YOUR_USER_ID';
   ```

3. **从 Android App 日志获取**：

   - 在 app 中查看 FCM token 注册日志
   - 或使用 adb logcat 查看

4. **使用注册脚本手动注册**：
   当 app 开发未就绪时，可以使用 `tools/scripts/fcm/register_fcm_token.py` 脚本手动注册 token 到数据库。

   ```bash
   # 基本用法：为指定用户注册 token
   python tools/scripts/fcm/register_fcm_token.py \
     --token "YOUR_FCM_TOKEN" \
     --user-id "USER_ID"

   # 验证 token 格式后注册（推荐）
   python tools/scripts/fcm/register_fcm_token.py \
     --token "YOUR_FCM_TOKEN" \
     --user-id "USER_ID" \
     --validate-token
   ```

   **使用场景**：

   - 测试推送功能时，需要手动注册 token
   - 从 Firebase Console 或其他渠道获取的 token 需要注册到数据库
   - 验证 token 格式是否正确

   **注意事项**：

   - 脚本会验证用户是否存在，如果用户不存在会报错
   - 如果 token 已存在，会更新关联的用户 ID
   - 使用 `--validate-token` 可以提前验证 token 格式

### 方法 3: Firebase Console 测试

Firebase Console 提供了图形界面来测试 FCM 推送。

#### 步骤

1. **登录 Firebase Console**

   - 访问 https://console.firebase.google.com
   - 选择项目

2. **进入 Cloud Messaging**

   - 左侧菜单 > Engage > Cloud Messaging
   - 点击 "Send test message"

3. **发送测试消息**

   - 输入 FCM registration token
   - 输入通知标题和内容
   - 点击 "Test"

4. **查看结果**
   - 成功：显示 "Message sent successfully"
   - 失败：显示错误信息

#### 查看发送历史

- Firebase Console > Cloud Messaging > Reports
- 可以查看消息发送统计和历史

### 方法 4: 使用 FCM REST API

直接使用 curl 调用 FCM REST API 进行测试。

#### 获取访问令牌

```bash
# 使用服务账号获取访问令牌
gcloud auth print-access-token
```

#### 发送测试消息

```bash
curl -X POST https://fcm.googleapis.com/v1/projects/PROJECT_ID/messages:send \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "token": "YOUR_FCM_TOKEN",
      "notification": {
        "title": "测试标题",
        "body": "测试内容"
      },
      "data": {
        "key": "value"
      }
    }
  }'
```

#### Dry Run 模式（REST API）

```bash
curl -X POST https://fcm.googleapis.com/v1/projects/PROJECT_ID/messages:send \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "validate_only": true,
    "message": {
      "token": "YOUR_FCM_TOKEN",
      "notification": {
        "title": "测试标题",
        "body": "测试内容"
      }
    }
  }'
```

### 方法 5: 增强日志调试

代码中已经增强了日志记录，可以通过日志查看详细信息。

#### 查看日志

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 查看结构化日志
tail -f logs/structured.log
```

#### 日志级别

- `INFO`: 正常操作信息
- `DEBUG`: 详细调试信息（包括 message_id、token 等）
- `WARNING`: 警告信息（如无效 token）
- `ERROR`: 错误信息（包括错误堆栈）

#### 关键日志信息

- `[DRY RUN]`: Dry run 模式标记
- `message_id`: FCM 返回的消息 ID
- `token`: 设备 token（部分显示）
- `error_type`: 错误类型
- `发送结果详情`: 详细的发送结果

## 常见问题排查

### 1. Token 无效

**症状**：

- 错误：`UnregisteredError` 或 `InvalidArgumentError`
- 日志显示 "Token 未注册" 或 "Token 格式无效"

**解决方法**：

1. 检查 token 格式是否正确
2. 检查 token 是否已过期
3. 检查 token 是否属于正确的项目
4. 使用 dry run 模式验证 token

### 2. Firebase 配置错误

**症状**：

- 错误：`SenderIdMismatchError`
- 初始化失败

**解决方法**：

1. 检查 `config.yaml` 中的 `firebase.service_account_path`
2. 确认服务账号文件存在且有效
3. 确认项目 ID 正确
4. 检查服务账号权限（需要 Firebase Cloud Messaging Admin 角色）

### 3. 消息格式错误

**症状**：

- Dry run 模式验证失败
- 错误信息提示格式问题

**解决方法**：

1. 检查消息字段是否符合 FCM 规范
2. 检查 data 字段的值是否为字符串（FCM 要求）
3. 检查图片 URL 是否有效
4. 使用测试脚本验证消息格式

### 4. 没有设备 Token

**症状**：

- 日志显示 "Users [...] have no registered device tokens"
- 返回 False

**解决方法**：

1. 检查数据库中是否有 device_tokens 记录
2. 确认用户已注册 device token
3. 检查 token 注册 API 是否正常工作

## 调试检查清单

### 配置检查

- [ ] Firebase 服务账号文件存在且有效
- [ ] `config.yaml` 中 `firebase.service_account_path` 配置正确
- [ ] Firebase Admin SDK 初始化成功
- [ ] 项目 ID 配置正确

### 数据库检查

- [ ] `device_tokens` 表存在
- [ ] 有测试用户的 device token 记录
- [ ] Token 格式正确（长度、字符等）

### 代码检查

- [ ] `notification_service.send_fcm_multicast` 函数可调用
- [ ] Dry run 模式正常工作
- [ ] 日志输出正常
- [ ] 错误处理正确

### 测试检查

- [ ] Dry run 模式验证通过
- [ ] 测试脚本可以运行
- [ ] 日志显示正确的信息
- [ ] 错误信息清晰明确

## 测试流程建议

### 第一步：Dry Run 验证

```bash
# 使用 dry run 模式验证配置
python tools/scripts/fcm/test_fcm_push.py --token TEST_TOKEN --dry-run
```

### 第二步：检查日志

查看日志确认：

- Firebase 初始化成功
- 消息格式验证通过
- 没有错误信息

### 第三步：真实发送测试（可选）

```bash
# 仅在确认配置正确后使用真实发送
python tools/scripts/fcm/test_fcm_push.py --token TEST_TOKEN --real
```

### 第四步：集成测试

测试完整的推送服务流程：

```bash
python tools/scripts/fcm/test_fcm_push.py --test-push-service --user-id USER_ID --dry-run
```

## 相关文件

- `app/services/notification_service.py` - FCM 推送服务
- `tools/scripts/fcm/test_fcm_push.py` - FCM 测试脚本
- `tools/scripts/fcm/register_fcm_token.py` - FCM Token 注册脚本
- `app/external_services/firebase.py` - Firebase 初始化
- `docs/PUSH_NOTIFICATION_SYSTEM.md` - 推送系统文档

## 参考资源

- [Firebase Cloud Messaging 文档](https://firebase.google.com/docs/cloud-messaging)
- [Firebase Admin SDK Python 文档](https://firebase.google.com/docs/reference/admin/python/firebase_admin.messaging)
- [FCM REST API 文档](https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages)
