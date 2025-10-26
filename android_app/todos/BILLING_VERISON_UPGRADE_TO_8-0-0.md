# 计费库 8.0.0 迁移计划

＃＃ 概述

从 Google Play 结算库 7.0.0 迁移到 8.0。0，替换所有 deprecated`SkuDetails`API 与新的用法`ProductDetails`__保留__12__。

## 风险评估

### 高风险区域

- **购买流程中断**：任何错误都可能导致 prevent 用户无法购买订阅
- **Price 显示错误**：不正确的 price 提取可能会向用户显示错误的 price
- **后端兼容性**：需要确保验证流程仍然适用于新的 API

### 中等风险区域

- **向后兼容性**：旧的购买仍应正确处理
- **错误处理**：新的错误代码和响应需要 proper 处理

### 低风险区域

- **连接处理**：BillingClient 连接逻辑基本保持不变- **存储层**：本地持久化不变

## 预计工作量

|任务|预计时间 |复杂性 |

|------|----------------|------------|

|依赖更新 | 5 分钟 |低|

| BillingPriceManager 重构 | 2-3小时|高|

| BillingPurchaseManager 重构 | 2-3小时|高|

|计费模型更新 | 30 分钟 |低|

|测试与调试| 3-4小时|高|

| **总计** | **8-11 小时** | **高** |

## 8.0.0 中的重大变化

### 删除了 APIs （会导致编译错误）1.✗`SkuDetails` and `SkuDetailsParams`
2. ✗ `querySkuDetailsAsync()`
3. ✗ `BillingFlowParams.Builder.setSkuDetails()`
4. ✗ `BillingClient.SkuType.SUBS`
5. ✗ `enablePendingPurchases()`（无参数版本）

### 需要新的 APIs

1.✓`ProductDetails` and `QueryProductDetailsParams`
2. ✓ `queryProductDetailsAsync()`
3. ✓ `BillingFlowParams.Builder.setProductDetailsParamsList()`
4. ✓ `ProductType.SUBS`
5. ✓ `enablePendingPurchases(PendingPurchasesParams.newBuilder().build())`---

## 详细迁移步骤

### 步骤 1：更新 Gradle 依赖项（5 分钟）

**文件**：`android_app/gradle/libs.versions.toml`

```toml
# Line 69: Change from 7.0.0 to 8.0.0
billingKtx = "8.0.0"
```**风险**：低 - 简单版本碰撞

**测试**：同步 Gradle 并检查是否存在即时编译错误

---

### 步骤 2：更新 BillingRepository 初始化（15 分钟）

**文件**：`BillingRepository.kt`（92-96号线）

**当前的**：```kotlin
billingClient = BillingClient.newBuilder(context.applicationContext)
    .setListener(this)
    .enablePendingPurchases()  // ❌ Deprecated
    .build()
```

**New**:

```kotlin
import com.android.billingclient.api.PendingPurchasesParams

billingClient = BillingClient.newBuilder(context.applicationContext)
    .setListener(this)
    .enablePendingPurchases(
        PendingPurchasesParams.newBuilder().enableOneTimeProducts().build()
    )
    .build()
```**风险**：低 - 有详细记录的变更

**测试**：确保 BillingClient 连接成功

---

### 步骤 3：重构 BillingPriceManager（2-3 小时）

**文件**：`BillingPriceManager.kt`- 需要完全重写

#### 3.1 更新导入```kotlin
// Remove:
import com.android.billingclient.api.SkuDetails
import com.android.billingclient.api.SkuDetailsParams

// Add:
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.ProductDetailsResponseListener
```#### 3.2 替换querySkuDetails()方法（第21-126行）

**当前签名**：```kotlin
fun querySkuDetails(isConnected: Boolean)
```**主要变化**：

**旧Pr产品清单大楼**：```kotlin
// ❌ Old way (Lines 39-43)
val params = SkuDetailsParams.newBuilder()
    .setSkusList(subscriptionIds)
    .setType(BillingClient.SkuType.SUBS)
    .build()
```**新Pr产品列表构建**：```kotlin
// ✓ New way
val productList = subscriptionIds.map { productId ->
    QueryProductDetailsParams.Product.newBuilder()
        .setProductId(productId)
        .setProductType(BillingClient.ProductType.SUBS)
        .build()
}

val params = QueryProductDetailsParams.newBuilder()
    .setProductList(productList)
    .build()
```**旧的异步查询**：```kotlin
// ❌ Old callback (Line 45)
billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
    // ...
}
```**新的异步查询**：```kotlin
// ✓ New callback
billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsList ->
    // Handle response
}
```#### 3.3 更新Price提取逻辑（第128-200行）

**当前方法签名**：```kotlin
private fun updateLocalPlans(currentPlans: List<VipPlan>, skuDetailsList: List<SkuDetails>)
```**新方法签名**：```kotlin
private fun updateLocalPlans(currentPlans: List<VipPlan>, productDetailsList: List<ProductDetails>)
```**Pr冰提取变化**：

**旧 SkuDetails API** （第 134-143 行）：```kotlin
skuDetails.forEach { skuDetails ->
    val planId = skuDetails.sku  // ❌ Deprecated
    val formattedPrice = skuDetails.price  // ❌ Deprecated
    val currencyCode = skuDetails.priceCurrencyCode  // ❌ Deprecated
    val micros = skuDetails.priceAmountMicros  // ❌ Deprecated
}
```**新Pr产品详细信息API**：```kotlin
productDetailsList.forEach { productDetails ->
    val planId = productDetails.productId  // ✓ New
    
    // For subscriptions, get the offer token and pricing info
    val subscriptionOfferDetails = productDetails.subscriptionOfferDetails?.firstOrNull()
    val pricingPhase = subscriptionOfferDetails?.pricingPhases?.pricingPhaseList?.firstOrNull()
    
    val formattedPrice = pricingPhase?.formattedPrice ?: "-"
    val currencyCode = pricingPhase?.priceCurrencyCode ?: ""
    val micros = pricingPhase?.priceAmountMicros ?: 0L
}
```**关键复杂性**：

- SkuDetails 具有扁平结构
- ProductDetails 具有嵌套结构：`subscriptionOfferDetails -> pricingPhases -> pricingPhaseList`- 需要处理多个优惠和 pricing 阶段（基本计划、promotional 优惠）

**风险**：高 - 复杂的嵌套结构，对于 price 显示至关重要

---

### 步骤4：重构BillingPurchaseManager（2-3小时）

**文件**：`BillingPurchaseManager.kt`#### 4.1 更新 launchBillingFlowInternal()（第 401-500 行）

**旧的 Product 查询**（第 403-407 行）：```kotlin
val params = SkuDetailsParams.newBuilder()
    .setSkusList(listOf(productId))
    .setType(BillingClient.SkuType.SUBS)  // ❌ Deprecated
    .build()

billingClient.querySkuDetailsAsync(params) { billingResult, skuDetailsList ->
```**新Pr产品查询**：```kotlin
val product = QueryProductDetailsParams.Product.newBuilder()
    .setProductId(productId)
    .setProductType(BillingClient.ProductType.SUBS)  // ✓ New
    .build()

val params = QueryProductDetailsParams.newBuilder()
    .setProductList(listOf(product))
    .build()

billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsList ->
```#### 4.2 更新 BillingFlowParams 构造（第 434-435 行）

**旧流量参数**：```kotlin
// ❌ Line 434-435
val billingFlowParams = BillingFlowParams.newBuilder()
    .setSkuDetails(skuDetails)
    .build()
```**新流量参数**：```kotlin
// ✓ New way - must specify offer token
val productDetails = productDetailsList.first()
val offerToken = productDetails.subscriptionOfferDetails?.firstOrNull()?.offerToken ?: ""

val productDetailsParams = BillingFlowParams.ProductDetailsParams.newBuilder()
    .setProductDetails(productDetails)
    .setOfferToken(offerToken)  // ⚠️ Required for subscriptions
    .build()

val billingFlowParams = BillingFlowParams.newBuilder()
    .setProductDetailsParamsList(listOf(productDetailsParams))
    .build()
```**重要**：订阅现在需要提供令牌。丢失代币将导致购买失败。

**风险**：高 - 对购买流程至关重要

#### 4.3 更新日志记录（第 417-431 行）

**旧 Property 访问权限**：```kotlin
skuDetails.sku          // ❌ Changed
skuDetails.title        // ✓ Still works
skuDetails.description  // ✓ Still works
skuDetails.price        // ❌ Changed
skuDetails.priceCurrencyCode  // ❌ Changed
```**新的 Property 访问权限**：```kotlin
productDetails.productId  // ✓ New
productDetails.title
productDetails.description
// Price extraction requires diving into subscriptionOfferDetails
val pricingPhase = productDetails.subscriptionOfferDetails
    ?.firstOrNull()?.pricingPhases?.pricingPhaseList?.firstOrNull()
val price = pricingPhase?.formattedPrice
val currencyCode = pricingPhase?.priceCurrencyCode
```---

### 第 5 步：更新事件模型（30 分钟）

**文件**：`BillingModels.kt`（32号线）

**当前的**：```kotlin
data class SkuDetailsQueryFailed(val code: Int, val message: String) : BillingEvent()
```**建议重命名**：```kotlin
data class ProductDetailsQueryFailed(val code: Int, val message: String) : BillingEvent()
```**影响**：需要更新以下位置的所有引用：

-`BillingPriceManager.kt`（73、86、103、112、117 号线）
- 任何监听此事件的 UI 代码

**风险**：低 - 简单重命名，但需要更新多个调用站点

---

### 步骤 6：添加 Null 安全处理（1 小时）

新的 ProductDetails API 有更多可为空的字段。添加强大的空检查：```kotlin
// Helper extension function to add
fun ProductDetails.getFirstOfferToken(): String? {
    return this.subscriptionOfferDetails?.firstOrNull()?.offerToken
}

fun ProductDetails.getBasePlanPrice(): Triple<String, String, Long>? {
    val pricingPhase = this.subscriptionOfferDetails
        ?.firstOrNull()
        ?.pricingPhases
        ?.pricingPhaseList
        ?.firstOrNull()
    
    return pricingPhase?.let {
        Triple(
            it.formattedPrice,
            it.priceCurrencyCode,
            it.priceAmountMicros
        )
    }
}
```**风险**：中 - 缺少空检查可能会导致崩溃

---

### 第 7 步：测试策略（3-4 小时）

#### 7.1 单元测试

- [ ] 使用有效的 product ID 测试 product 详细信息查询
- [ ] 使用无效的 product ID 测试 product 详细信息查询
- [ ] 测试从 ProductDetails 中提取 price
- [ ] 测试报价令牌提取
- [ ] 测试缺失报价的空处理

#### 7.2 集成测试

- [ ] 在调试版本中连接到 Google Play Billing
- [ ] 验证 prices 在 VIP 中心正确显示
- [ ] 通过测试订阅测试完整的购买流程
- [ ] 验证购买确认有效- [ ] 测试后端验证是否仍然有效
- [ ] 测试错误处理（网络错误、服务不可用）

#### 7.3 边缘情况

- [ ] 多项订阅优惠 (promotional prices)
- [ ] 免费试用优惠
- [ ] 没有可用的优惠
- [ ] 计费客户端查询期间断开连接
- [ ] 购买时的应用程序后台

#### 7.4 回归测试

- [ ] 验证现有购买是否仍可识别
- [ ] 正确检查订阅状态更新
- [ ] 确保本地缓存/存储仍然有效
- [ ] 测试自动续订状态跟踪

---

## 需要更改的文件

|文件 |线路变更 |复杂性 | Pr优先级||------|--------------|------------|----------|

|`libs.versions.toml` | 1 | Low | P0 |

| `BillingRepository.kt` | 5 | Low | P0 |

| `BillingPriceManager.kt`| 〜80 |高| P0|

|`BillingPurchaseManager.kt`| 〜60 |高| P0|

|`BillingModels.kt` | ~5 | Low | P1 |

| `BillingRemoteManager.kt`| 2 |低| P1 |

**总计**：6 个文件中更改了约 153 行

---

## 回滚计划

如果迁移后出现严重问题：

1.**立即**：恢复`billingKtx = "7.0.0"`在版本目录中
2. **恢复代码更改**：Git 恢复迁移提交
3. **紧急修补程序**：从发布分支发布previous版本
4.**时间线**：如果提早发现，可以在 1 小时内回滚

---

## 迁移清单

### Pre-迁移

- [ ] 创建功能分支`billing-8.0-migration`- [ ] 备份当前工作代码
- [ ] 查看 Google 官方迁移指南
- [ ] 设置测试 Google Play 管理中心 products

### 迁移期间

- [ ] 更新 Gradle 依赖
- [ ] 更新 BillingRepository 初始化
- [ ] 重构计费PriceManager
- [ ] 重构 BillingPurchaseManager
- [ ] 更新 BillingModels
- [ ] 添加空安全扩展
- [ ] 更新所有导入语句

### 迁移后

- [ ] 运行单元测试
- [ ] 使用真实计费进行调试构建测试
- [ ] 测试完整的购买流程
- [ ] 验证后端集成
- [ ] 在多个设备/Android版本上测试
- [ ] 检查日志中是否有任何警告- [ ] 性能测试（无回归）

### 释放Preparation

- [ ] 更新 CHANGELOG.md
- [ ] 记录任何新的错误代码
- [ ] Prepare回滚指令
- [ ] 阶段发布至内部测试轨道
- [ ] 密切监视崩溃报告

---

## 关键成功标准

1. ✓ 所有编译错误均已解决
2. ✓ Prices 在 UI 中正确显示
3. ✓ 购买流程成功完成
4. ✓ 后端验证不变
5. ✓ 计费代码中没有新的崩溃
6. ✓ 现有订阅仍然有效
7. ✓ 测试购买在调试版本中工作

---

## 预计时间表

|相|持续时间 |可以并行化|

|--------|----------|----------------||代码更改 | 5-6 小时 |没有 |

|测试| 3-4小时|部分|

|错误修复 | 1-2小时|没有 |

| **总计** | **9-12 小时** | - |

**建议**：为此迁移分配 2 个完整工作日，以解决意外问题。

---

## 附加说明

- **兼容性**：计费库 8.0.0 需要 Android Gradle 插件 7.0+
- **最低 SDK**：无变化（仍然支持 Android 4.4+）
- **重大变更**：这是一个重大的 API 重新设计，而不仅仅是简单的升级
- **Google 建议**：所有应用程序应在 2025 年第二季度之前迁移- **替代**：继续使用 7.0。0 仍然受支持，但 deprecated