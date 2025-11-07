# 订阅 Webhook 补偿方案计划

## 问题背景

### 当前问题
1. **用户已付款但数据库无订阅记录**：Google Play 订单已处理，但后端数据库中没有对应的订阅记录
2. **Webhook 无法推断用户ID**：类型4（SUBSCRIPTION_PURCHASED）的 webhook 通知无法从购买信息中推断用户ID，因为：
   - `email_address`、`profile_id`、`developer_payload` 在 Google Play API 响应中通常为 `None`
   - `developer_payload` 已被弃用（Google Play 结算库 3.0+ 已移除）
3. **Webhook 先于 Verify 到达**：Webhook 通知通常在 app 端调用 verify 接口之前到达，导致无法通过 webhook 创建订阅记录

### 影响
- 用户已付款但无法使用订阅功能
- 可能导致用户申请退款
- 数据不一致：Google Play 有记录，后端没有

## 方案确认

### 1. Google Play API 响应字段确认

**需要确认的字段：**
- `obfuscatedExternalAccountId`：混淆的外部账号ID（如果 app 端设置了 `setObfuscatedAccountId()`）
- `obfuscatedExternalProfileId`：混淆的外部个人资料ID（如果 app 端设置了 `setObfuscatedProfileId()`）

**确认方式：**
1. 查看实际 Google Play API 响应（通过日志或测试脚本）
2. 检查 `raw_response` 字段中是否包含这些字段
3. 如果存在，字段名称可能为：
   - `obfuscatedExternalAccountId`
   - `obfuscatedExternalProfileId`
   - 或其他变体

**当前代码状态：**
- `_parse_subscription_purchase` 方法未解析这些字段
- `_infer_user_id_from_purchase_info` 方法未使用这些字段

### 2. ObfuscatedAccountId 工作原理

根据 [Google Play 官方文档](https://developer.android.com/google/play/billing/developer-payload?hl=zh-cn)：

1. **App 端设置**：在购买时使用 `BillingFlowParams.Builder.setObfuscatedAccountId(userId)` 设置用户ID
2. **Google Play 存储**：Google Play 会存储这个混淆的账号ID
3. **API 返回**：Google Play Developer API 的响应中可能包含 `obfuscatedExternalAccountId` 字段
4. **服务器端使用**：服务器端可以通过这个字段关联用户

**注意**：
- ObfuscatedAccountId 是混淆的，不是原始用户ID
- 需要在数据库中存储映射关系（用户ID <-> ObfuscatedAccountId）
- 或者直接使用 ObfuscatedAccountId 作为用户标识（如果 app 端设置的是用户ID的某种编码）

## 实施方案

### 阶段1：确认和基础支持（立即）

#### 1.1 确认 Google Play API 响应格式
- [ ] 添加日志记录，输出完整的 Google Play API 响应（`raw_response`）
- [ ] 检查实际响应中是否包含 `obfuscatedExternalAccountId` 或类似字段
- [ ] 确认字段名称和格式

#### 1.2 更新解析逻辑
- [ ] 在 `_parse_subscription_purchase` 方法中添加对 ObfuscatedAccountId 字段的解析
- [ ] 字段名称可能为：`obfuscatedExternalAccountId`、`obfuscatedAccountId` 等
- [ ] 同时解析 `obfuscatedExternalProfileId`（如果存在）

**代码位置：** `app/external_services/google_play_service.py:212-240`

### 阶段2：用户推断逻辑优化（短期）

#### 2.1 更新用户推断方法
- [ ] 在 `_infer_user_id_from_purchase_info` 方法中添加通过 ObfuscatedAccountId 查找用户的逻辑
- [ ] 方案A：如果 ObfuscatedAccountId 就是用户ID的某种编码，直接使用
- [ ] 方案B：在数据库中存储映射关系（`user_obfuscated_accounts` 表）
- [ ] 优先级：ObfuscatedAccountId > email > profile_id > order_id

**代码位置：** `app/services/subscription_service.py:1324-1375`

#### 2.2 数据库设计（如果需要）
- [ ] 如果需要存储映射关系，创建 `user_obfuscated_accounts` 表：
  - `user_id` (FK to users.id)
  - `obfuscated_account_id` (unique)
  - `created_at`
  - `updated_at`
- [ ] 在用户首次购买时创建映射记录
- [ ] 在 verify 接口中创建映射记录（如果不存在）

### 阶段3：Webhook 处理优化（短期）

#### 3.1 恢复类型4的订阅创建逻辑
- [ ] 修改 `_try_create_subscription_from_notification` 方法，恢复对类型4的处理
- [ ] 但仅在能够推断用户ID的情况下才创建订阅记录
- [ ] 如果无法推断用户ID，记录 INFO 日志并返回 True（等待 verify 接口）

**代码位置：** `app/services/subscription_service.py:1227-1318`

#### 3.2 优化日志记录
- [ ] 区分"无法推断用户ID（正常）"和"其他错误"
- [ ] 使用 INFO 级别记录无法推断用户ID的情况
- [ ] 使用 WARNING 级别记录其他错误

### 阶段4：Verify 接口优化（短期）

#### 4.1 处理重复 purchase_token
- [ ] 优化 `verify_and_create_subscription` 方法
- [ ] 如果 purchase_token 已存在：
  - 检查是否属于当前用户
  - 如果属于当前用户，返回成功并返回现有订阅记录
  - 如果不属于当前用户，返回错误（安全考虑）

**代码位置：** `app/services/subscription_service.py:363-377`

**实现逻辑：**
```python
if existing_subscription:
    # 检查是否属于当前用户
    if existing_subscription.user_id == user_id:
        # 属于当前用户，返回成功
        logger.info(f"订阅已存在，返回现有订阅记录: {existing_subscription.id}")
        # 重新查询订阅记录以确保关联对象被正确加载
        result = await db.execute(
            select(UserSubscription)
            .options(selectinload(UserSubscription.plan))
            .where(UserSubscription.id == existing_subscription.id)
        )
        subscription = result.scalar_one()
        subscription_schema = UserSubscriptionSchema.model_validate(subscription)
        return PurchaseVerificationResponse(
            is_verified=True,
            subscription=subscription_schema,
            message="订阅已验证（已存在）",
        )
    else:
        # 不属于当前用户，返回错误
        return PurchaseVerificationResponse(
            is_verified=False,
            subscription=None,
            message="该购买令牌已被其他用户使用",
            error_code="DUPLICATE_PURCHASE_TOKEN_DIFFERENT_USER",
        )
```

### 阶段5：App 端集成（中期）

#### 5.1 设置 ObfuscatedAccountId
- [ ] 在 Android app 的购买流程中，使用 `BillingFlowParams.Builder.setObfuscatedAccountId(userId)` 设置用户ID
- [ ] 确保 userId 是用户的唯一标识符（建议使用用户ID的某种编码或哈希）

**代码位置：** `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/billing/BillingPurchaseManager.kt`

**实现示例：**
```kotlin
val billingFlowParams = BillingFlowParams.newBuilder()
    .setProductDetailsParamsList(listOf(productDetailsParams))
    .setObfuscatedAccountId(userId)  // 设置用户ID
    .build()
```

#### 5.2 向后兼容
- [ ] 确保旧版本 app（未设置 ObfuscatedAccountId）仍能正常工作
- [ ] 对于没有 ObfuscatedAccountId 的购买，回退到现有的 verify 接口流程

### 阶段6：补偿机制（中期）

#### 6.1 延迟补偿
- [ ] 对于类型4的 webhook，如果无法创建订阅记录，将购买信息存入临时表
- [ ] 用户下次打开 app 时，app 端调用 verify 接口
- [ ] Verify 接口检查临时表，如果存在则创建订阅记录并清理临时数据

**数据库设计：**
```sql
CREATE TABLE pending_subscription_creates (
    id UUID PRIMARY KEY,
    purchase_token VARCHAR(255) UNIQUE NOT NULL,
    order_id VARCHAR(255),
    product_id VARCHAR(255),
    purchase_info JSONB,
    notification_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE  -- 7天后过期
);
```

#### 6.2 定期扫描补偿
- [ ] 创建定期任务，扫描 Google Play 订单
- [ ] 检查数据库中是否有对应的订阅记录
- [ ] 如果没有，尝试通过其他方式关联用户（如订单时间、设备信息等）
- [ ] 如果仍无法关联，标记为待处理，由管理员手动处理

#### 6.3 手动补偿接口（紧急）
- [ ] 创建管理接口，允许管理员手动创建订阅记录
- [ ] 输入：`purchase_token` 或 `order_id`、`user_id`
- [ ] 验证 Google Play 订单
- [ ] 创建订阅记录

## 实施优先级

### 立即（P0）
1. ✅ 优化 verify 接口处理重复 purchase_token 的逻辑（阶段4）
2. ✅ 恢复类型4的 webhook 处理，但仅在能推断用户ID时创建（阶段3.1）

### 短期（P1）
3. 确认 Google Play API 响应格式（阶段1.1）
4. 更新解析逻辑支持 ObfuscatedAccountId（阶段1.2）
5. 更新用户推断逻辑（阶段2.1）

### 中期（P2）
6. App 端设置 ObfuscatedAccountId（阶段5）
7. 实现延迟补偿机制（阶段6.1）
8. 实现定期扫描补偿（阶段6.2）

### 长期（P3）
9. 实现手动补偿接口（阶段6.3）

## 测试计划

### 单元测试
- [ ] 测试 `_parse_subscription_purchase` 解析 ObfuscatedAccountId
- [ ] 测试 `_infer_user_id_from_purchase_info` 通过 ObfuscatedAccountId 查找用户
- [ ] 测试 `verify_and_create_subscription` 处理重复 purchase_token

### 集成测试
- [ ] 测试 webhook 先于 verify 到达的场景
- [ ] 测试 verify 接口处理已存在订阅记录的场景
- [ ] 测试 app 端设置 ObfuscatedAccountId 后的完整流程

### 端到端测试
- [ ] 完整购买流程测试
- [ ] Webhook 补偿流程测试
- [ ] 错误场景测试（网络失败、API 失败等）

## 风险评估

### 风险1：Google Play API 不返回 ObfuscatedAccountId
- **概率**：中等
- **影响**：无法通过 webhook 创建订阅记录
- **缓解**：回退到现有的 verify 接口流程

### 风险2：ObfuscatedAccountId 格式不一致
- **概率**：低
- **影响**：无法正确关联用户
- **缓解**：在 app 端使用统一的编码格式

### 风险3：Webhook 和 Verify 并发处理
- **概率**：高
- **影响**：可能导致重复创建订阅记录
- **缓解**：使用数据库唯一约束和事务处理

## 监控和告警

### 关键指标
- Webhook 处理成功率
- Verify 接口调用成功率
- 订阅记录创建延迟
- 无法推断用户ID的 webhook 数量

### 告警规则
- Webhook 处理失败率 > 5%
- Verify 接口失败率 > 1%
- 订阅记录创建延迟 > 10秒

## 文档更新

- [ ] 更新 API 文档，说明 ObfuscatedAccountId 的使用
- [ ] 更新开发文档，说明 webhook 和 verify 的处理流程
- [ ] 更新运维文档，说明补偿机制和手动处理流程

## 参考资料

- [Google Play 开发者载荷文档](https://developer.android.com/google/play/billing/developer-payload?hl=zh-cn)
- [Google Play Developer API 文档](https://developers.google.com/android-publisher/api-ref/rest/v3/purchases.subscriptions/get)
- [Google Play 结算库文档](https://developer.android.com/google/play/billing)

