# Google Play Console 订阅配置指南

## 概述

本指南详细介绍如何在 Google Play Console 中配置订阅商品，以及如何与后端 API 对接。

## 1. Google Play Console 配置步骤

### 1.1 创建订阅商品

每种订阅计划都需要在 Google Play Console 中创建一个独立的商品：

1. **登录 Google Play Console**

   - 访问 [Google Play Console](https://play.google.com/console)
   - 选择您的应用

2. **进入订阅设置**

   - 左侧菜单：`盈利` -> `应用内产品` -> `订阅`
   - 点击 `创建订阅`

3. **创建三种订阅商品**

   需要创建以下三种商品：

   | 商品名称          | Product ID                      | 价格   | 周期    | 描述         |
   | ----------------- | ------------------------------- | ------ | ------- | ------------ |
   | Premium Monthly   | `com.ai.inty.premium.monthly`   | $9.99  | 1 个月  | 月度高级订阅 |
   | Premium Quarterly | `com.ai.inty.premium.quarterly` | $24.99 | 3 个月  | 季度高级订阅 |
   | Premium Yearly    | `com.ai.inty.premium.annual`    | $79.99 | 12 个月 | 年度高级订阅 |

   **⚠️ 重要说明：**

   - `Product ID` 必须与数据库中的 `google_play_product_id` 字段完全一致
   - 不能修改已发布的 Product ID
   - 建议使用版本号（如 v1）以便将来升级

### 1.2 配置订阅详情

为每个订阅商品配置：

1. **基本信息**

   - 商品名称：用户可见的名称
   - 商品描述：详细的功能说明
   - 价格：根据目标市场设置

2. **订阅周期**

   - 月度：1 个月
   - 季度：3 个月
   - 年度：12 个月

3. **免费试用期**（可选）

   - 建议设置 7 天免费试用
   - 有助于提高转化率

4. **宽限期**（推荐）
   - 设置 3-7 天宽限期
   - 防止因支付问题导致的订阅中断

### 1.3 配置 Google Play Developer API

**重要说明**：Google Play Console 和 Google Cloud Console 可以使用不同的 Google 账号，但需要正确配置权限关联。

#### 方案一：使用相同 Google 账号（推荐）

1. **使用相同账号登录两个平台**
   - Google Play Console：管理应用和订阅
   - Google Cloud Console：创建服务账号和 API

#### 方案二：使用不同 Google 账号

1. **Google Cloud Console 操作**（技术团队账号）

   - 访问 [Google Cloud Console](https://console.cloud.google.com/)
   - 创建或选择项目
   - 启用 `Google Play Developer API`
   - 创建服务账号：
     ```
     项目 -> IAM 与管理 -> 服务账号 -> 创建服务账号
     ```
   - 下载服务账号密钥文件（JSON 格式）
   - 记录服务账号邮箱地址（如：`my-service@my-project.iam.gserviceaccount.com`）

2. **Google Play Console 操作**（发布者账号）

   - 登录 [Google Play Console](https://play.google.com/console)
   - 进入 `设置` -> `API权限`
   - 点击 `关联项目`
   - 输入 Google Cloud 项目 ID
   - 关联项目后，添加服务账号：
     - 点击 `创建新的服务账号` 或 `使用现有服务账号`
     - 输入在 Google Cloud 中创建的服务账号邮箱
     - 授予权限：
       - ✅ 查看财务报告
       - ✅ 查看应用信息和下载批量报告
       - ✅ 管理订单和订阅

3. **验证配置**
   - 在 Google Play Console 的 API 权限页面确认服务账号已添加
   - 确认权限包括：`查看财务报告`、`管理订单和订阅`

#### 配置详细步骤

1. **启用 Google Play Developer API**

   ```bash
   # 在 Google Cloud Console 中启用 API
   gcloud services enable androidpublisher.googleapis.com
   ```

2. **创建服务账号**

   ```bash
   # 创建服务账号
   gcloud iam service-accounts create google-play-api \
     --description="Google Play Developer API Service Account" \
     --display-name="Google Play API"

   # 创建密钥文件
   gcloud iam service-accounts keys create google-play-service-key.json \
     --iam-account=google-play-api@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

3. **Google Play Console 权限配置**
   - 进入 `设置` -> `API权限`
   - 如果使用不同账号，首先 `关联项目`
   - 添加服务账号邮箱：`google-play-api@YOUR_PROJECT_ID.iam.gserviceaccount.com`
   - 选择权限：
     - ✅ 查看财务报告
     - ✅ 管理订单和订阅
     - ✅ 查看应用信息和下载批量报告

### 1.4 配置 Webhook 通知

1. **创建 Cloud Pub/Sub 主题**

   ```bash
   # 创建主题
   gcloud pubsub topics create play-notifications

   # 创建订阅
   gcloud pubsub subscriptions create play-sub \
     --topic=play-notifications \
     --push-endpoint=https://your-api.com/api/v1/subscription/webhook
   ```

2. **在 Google Play Console 中配置通知**
   - 进入 `设置` -> `开发者账号` -> `API权限`
   - 配置 `实时开发者通知`
   - 设置 Pub/Sub 主题名称

## 2. 后端 API 集成

### 2.1 环境变量配置

在 `config.yaml` 中配置以下参数：

```yaml
google_play:
  package_name: "com.your.app"
  service_account_key_path: "/path/to/service-account-key.json"
  webhook_secret: "your-webhook-secret-key"
# 或者使用环境变量
# GOOGLE_PLAY_PACKAGE_NAME=com.your.app
# GOOGLE_PLAY_SERVICE_ACCOUNT_KEY_PATH=/path/to/service-account-key.json
# GOOGLE_PLAY_WEBHOOK_SECRET=your-webhook-secret-key
```

### 2.2 API 接口说明

#### 获取订阅计划

```http
GET /api/v1/subscription/plans
Authorization: Bearer <token>
```

#### 验证购买

```http
POST /api/v1/subscription/verify
Authorization: Bearer <token>
Content-Type: application/json

{
  "product_id": "premium_monthly_v1",
  "purchase_token": "purchase_token_from_google_play",
  "order_id": "order_id_from_google_play"
}
```

#### 查询订阅状态

```http
GET /api/v1/subscription/status
Authorization: Bearer <token>
```

## 3. App 端集成示例

### 3.1 Android 集成

在 Android 应用中集成 Google Play Billing：

```kotlin
// 1. 添加依赖
implementation "com.android.billingclient:billing:5.0.0"

// 2. 初始化BillingClient
private fun initializeBilling() {
    billingClient = BillingClient.newBuilder(this)
        .setListener(this)
        .enablePendingPurchases()
        .build()
}

// 3. 查询订阅商品
private fun querySubscriptionProducts() {
         val skuList = listOf(
         "com.ai.inty.premium.monthly",
         "com.ai.inty.premium.quarterly",
         "com.ai.inty.premium.annual"
     )

    val params = SkuDetailsParams.newBuilder()
        .setSkusList(skuList)
        .setType(BillingClient.SkuType.SUBS)
        .build()

    billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
        // 处理查询结果
    }
}

// 4. 发起购买
private fun launchPurchaseFlow(skuDetails: SkuDetails) {
    val flowParams = BillingFlowParams.newBuilder()
        .setSkuDetails(skuDetails)
        .build()

    billingClient.launchBillingFlow(this, flowParams)
}

// 5. 处理购买结果
override fun onPurchasesUpdated(billingResult: BillingResult, purchases: List<Purchase>?) {
    if (billingResult.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
        for (purchase in purchases) {
            // 调用后端API验证购买
            verifyPurchaseWithBackend(purchase)
        }
    }
}
```

### 3.2 验证购买流程

```kotlin
private fun verifyPurchaseWithBackend(purchase: Purchase) {
    val request = VerifyPurchaseRequest(
        productId = purchase.sku,
        purchaseToken = purchase.purchaseToken,
        orderId = purchase.orderId
    )

    // 调用后端API验证
    api.verifyPurchase(request) { response ->
        if (response.isValid) {
            // 验证成功，更新用户订阅状态
            updateUserSubscriptionStatus()
        } else {
            // 验证失败，处理错误
            handleVerificationError(response.message)
        }
    }
}
```

## 4. 测试流程

### 4.1 测试账号设置

1. **设置测试账号**

   - 在 Google Play Console 中添加测试账号
   - 测试账号可以免费购买订阅

2. **使用测试信用卡**
   - Google Play 提供测试信用卡号
   - 不会产生实际费用

### 4.2 测试步骤

1. **运行数据库迁移**

   ```bash
   alembic upgrade head
   ```

2. **初始化订阅计划**

   ```bash
   cd scripts
   python init_subscription_plans.py --action init
   ```

3. **查看创建的计划**

   ```bash
   python init_subscription_plans.py --action list
   ```

4. **测试 API 接口**

   ```bash
   # 获取订阅计划
   curl -X GET "http://localhost:8000/api/v1/subscription/plans" \
     -H "Authorization: Bearer <token>"

   # 验证购买
   curl -X POST "http://localhost:8000/api/v1/subscription/verify" \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "product_id": "com.ai.inty.premium.monthly",
       "purchase_token": "test_token",
       "order_id": "test_order"
     }'
   ```

## 5. 生产环境部署

### 5.1 环境变量配置

确保以下环境变量在生产环境中正确配置：

```bash
# Google Play配置
GOOGLE_PLAY_PACKAGE_NAME=com.your.app
GOOGLE_PLAY_SERVICE_ACCOUNT_KEY_PATH=/path/to/service-account-key.json
GOOGLE_PLAY_WEBHOOK_SECRET=your-webhook-secret-key

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/dbname

# 其他配置
JWT_SECRET_KEY=your-jwt-secret
```

### 5.2 安全注意事项

1. **服务账号密钥安全**

   - 不要将密钥文件提交到代码仓库
   - 使用环境变量或安全的密钥管理服务

2. **Webhook 验证**

   - 验证 Webhook 请求的签名
   - 使用 HTTPS 确保通信安全

3. **购买验证**
   - 所有购买都必须通过 Google Play API 验证
   - 不要信任客户端发送的购买信息

## 6. 常见问题

### Q1: Product ID 不匹配怎么办？

A: 确保数据库中的`google_play_product_id`与 Google Play Console 中的 Product ID 完全一致，包括大小写。

### Q2: 购买验证失败怎么办？

A: 检查以下因素：

- 服务账号权限是否正确配置
- Google Cloud 项目是否已关联到 Google Play Console
- API 配置是否正确
- 网络连接是否正常
- 服务账号密钥文件是否有效

### Q3: 使用不同 Google 账号时权限问题？

A: 确保以下步骤正确完成：

- Google Cloud 项目已在 Google Play Console 中关联
- 服务账号已添加到 Google Play Console 的 API 权限中
- 服务账号具有必要的权限（查看财务报告、管理订单和订阅）
- 项目 ID 和服务账号邮箱地址输入正确

### Q4: "Project not linked" 错误？

A: 这表示 Google Cloud 项目未与 Google Play Console 关联：

1. 在 Google Play Console 中进入 `设置` -> `API权限`
2. 点击 `关联项目`
3. 输入正确的 Google Cloud 项目 ID
4. 确认关联后再添加服务账号

### Q5: 服务账号无权限访问 API？

A: 检查以下配置：

```bash
# 确认服务账号权限
gcloud projects get-iam-policy YOUR_PROJECT_ID

# 如需要，添加基本权限
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:google-play-api@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/androidpublisher.subscriptionsViewer"
```

### Q6: Webhook 通知收不到怎么办？

A: 检查 Pub/Sub 配置、网络防火墙、HTTPS 证书等。

### Q7: 如何处理退款？

A: 系统会自动处理 Google Play 的退款通知，更新订阅状态。

### Q8: 测试环境下如何验证配置？

A: 使用以下方法验证：

```bash
# 测试 API 访问权限
curl -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/YOUR_PACKAGE_NAME"
```

## 7. 账号管理最佳实践

### 7.1 推荐的账号配置策略

| 场景                  | Google Play Console 账号 | Google Cloud Console 账号 | 优缺点                                            |
| --------------------- | ------------------------ | ------------------------- | ------------------------------------------------- |
| **小团队/个人开发者** | 主账号                   | 主账号                    | ✅ 简单易管理<br/>❌ 权限集中                     |
| **中大型团队**        | 发布者账号               | 技术团队账号              | ✅ 职责分离<br/>✅ 安全性高<br/>❌ 配置复杂       |
| **企业级**            | 企业主账号               | DevOps 团队账号           | ✅ 权限最小化<br/>✅ 审计追踪<br/>❌ 需要详细规划 |

### 7.2 权限配置检查清单

完成配置后，请确认以下权限设置：

**Google Cloud Console 检查：**

- [ ] Google Play Developer API 已启用
- [ ] 服务账号已创建
- [ ] 服务账号密钥文件已下载
- [ ] 项目 ID 已记录

**Google Play Console 检查：**

- [ ] Google Cloud 项目已关联
- [ ] 服务账号已添加到 API 权限
- [ ] 服务账号具有以下权限：
  - [ ] 查看财务报告
  - [ ] 管理订单和订阅
  - [ ] 查看应用信息和下载批量报告

**后端配置检查：**

- [ ] `config.yaml` 中 Google Play 配置正确
- [ ] 服务账号密钥文件路径正确
- [ ] 包名 (`package_name`) 与应用一致

### 7.3 安全建议

1. **服务账号密钥管理**

   ```bash
   # 设置密钥文件权限
   chmod 600 google-play-service-key.json

   # 使用环境变量而非硬编码路径
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-play-service-key.json
   ```

2. **定期轮换密钥**

   ```bash
   # 创建新密钥
   gcloud iam service-accounts keys create new-key.json \
     --iam-account=google-play-api@YOUR_PROJECT_ID.iam.gserviceaccount.com

   # 删除旧密钥
   gcloud iam service-accounts keys delete OLD_KEY_ID \
     --iam-account=google-play-api@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

3. **最小权限原则**
   - 只授予必要的权限
   - 定期审查权限设置
   - 记录权限变更日志

## 8. 监控和日志

建议配置以下监控：

1. **订阅转化率监控**
2. **购买验证成功率**
3. **Webhook 通知处理状态**
4. **用户订阅状态变化**
5. **API 调用错误率**
6. **Google Play API 配额使用情况**
7. **不同账号间的权限问题**

通过这些监控可以及时发现和解决问题，确保订阅系统的稳定运行。

### 8.1 常用监控指标

```bash
# Google Cloud 监控 API 调用
gcloud logging read "resource.type=gce_instance AND jsonPayload.message=~'Google Play'" --limit=50

# 检查 API 配额使用情况
gcloud services list --enabled --filter="name:androidpublisher.googleapis.com"
```
