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

   | 商品名称          | Product ID             | 价格   | 周期    | 描述         |
   | ----------------- | ---------------------- | ------ | ------- | ------------ |
   | Premium Monthly   | `premium_monthly_v1`   | $9.99  | 1 个月  | 月度高级订阅 |
   | Premium Quarterly | `premium_quarterly_v1` | $24.99 | 3 个月  | 季度高级订阅 |
   | Premium Yearly    | `premium_yearly_v1`    | $79.99 | 12 个月 | 年度高级订阅 |

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

1. **启用 Google Play Developer API**

   - 访问 [Google Cloud Console](https://console.cloud.google.com/)
   - 启用 `Google Play Developer API`

2. **创建服务账号**

   - 创建新的服务账号
   - 下载服务账号密钥文件（JSON 格式）
   - 将密钥文件路径配置到环境变量 `GOOGLE_SERVICE_ACCOUNT_KEY_PATH`

3. **配置 API 权限**
   - 在 Google Play Console 中，进入 `设置` -> `API权限`
   - 添加服务账号并授予必要权限
   - 权限包括：查看财务报告、管理订单和订阅

### 1.4 配置 Webhook 通知

1. **创建 Cloud Pub/Sub 主题**

   ```bash
   # 创建主题
   gcloud pubsub topics create google-play-notifications

   # 创建订阅
   gcloud pubsub subscriptions create google-play-sub \
     --topic=google-play-notifications \
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
        "premium_monthly_v1",
        "premium_quarterly_v1",
        "premium_yearly_v1"
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
       "product_id": "premium_monthly_v1",
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

A: 检查服务账号权限、API 配置、网络连接等因素。

### Q3: Webhook 通知收不到怎么办？

A: 检查 Pub/Sub 配置、网络防火墙、HTTPS 证书等。

### Q4: 如何处理退款？

A: 系统会自动处理 Google Play 的退款通知，更新订阅状态。

## 7. 监控和日志

建议配置以下监控：

1. **订阅转化率监控**
2. **购买验证成功率**
3. **Webhook 通知处理状态**
4. **用户订阅状态变化**
5. **API 调用错误率**

通过这些监控可以及时发现和解决问题，确保订阅系统的稳定运行。
