package com.ai.inty.billing

import android.content.Context
import com.ai.inty.net.ISubscriptionApi
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.SkuDetails
import com.architecture.httplib.core.HttpResult
import com.architecture.httplib.utils.MoshiUtils
import com.inty.utils.log.EasyLog
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 订阅状态数据类
 */
data class VipStatus(
    val isSubscribed: Boolean,
    val subscriptionId: String? = null,
    val purchaseTime: Long = 0L,
    val expiryTime: Long = 0L
)

 /**
  * 计费事件
  */
 sealed class BillingEvent {
     object Connected : BillingEvent()
     object Disconnected : BillingEvent()
     data class PurchaseSuccess(val purchase: Purchase) : BillingEvent()
     data class PurchaseFailed(val code: Int, val message: String) : BillingEvent()
     data class SkuDetailsQueryFailed(val code: Int, val message: String) : BillingEvent()
 }

/**
 * 会员计划数据类
 */
data class VipPlan(
    val googleProductId: String,
    val discountRate: Double,
    val name: String,
    val planType: String,
    val description: String,
    val price: String = "-", // 价格，初始为占位符
    val originalPrice: String = "-", // 原价
    val currencyCode: String = "", // 货币代码
    val priceAmountMicros: Long = 0L // 价格金额（微秒）
)

// Repository
object BillingRepository : PurchasesUpdatedListener, BillingClientStateListener {
    private lateinit var billingClient: BillingClient
    private var isConnected = false
    
    // 协程作用域，用于发送事件
    private val eventScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    
    private val _vipStatusFlow = MutableStateFlow<VipStatus>(VipStatus(isSubscribed = false))
    val vipStatusFlow: StateFlow<VipStatus> = _vipStatusFlow.asStateFlow()
    
    private val _plansFlow = MutableStateFlow<List<VipPlan>>(emptyList())
    val plansFlow: StateFlow<List<VipPlan>> = _plansFlow.asStateFlow()
    
    // 事件流，用于通知 UI 层计费状态变化
    private val _eventFlow = MutableSharedFlow<BillingEvent>()
    val eventFlow: SharedFlow<BillingEvent> = _eventFlow.asSharedFlow()
  
    private val api = TheRouter.get(ISubscriptionApi::class.java)!!
  
    init {
      // 应用启动先读本地
      _vipStatusFlow.value = getLocalVipStatus()
      _plansFlow.value = getLocalPlans()
    }
    
    /**
     * BillingClient
     */
    fun initialize(context: Context) {
        if (::billingClient.isInitialized) return

        // 打印设备区域和货币信息
        val locale = context.resources.configuration.locales[0]
        val currency = java.util.Currency.getInstance(locale)
        EasyLog.log("BillingRepository - 设备区域: ${locale.displayCountry} (${locale.country}), 货币: ${currency.displayName} (${currency.currencyCode})")

        // 检查设备信息
        EasyLog.log("BillingRepository - 设备信息:")
        EasyLog.log("  制造商: ${android.os.Build.MANUFACTURER}")
        EasyLog.log("  型号: ${android.os.Build.MODEL}")
        EasyLog.log("  Android 版本: ${android.os.Build.VERSION.RELEASE}")
        EasyLog.log("  API 级别: ${android.os.Build.VERSION.SDK_INT}")
        EasyLog.log("  是否模拟器: ${isEmulator()}")

        billingClient = BillingClient.newBuilder(context.applicationContext)
            .setListener(this)
            .enablePendingPurchases(
                PendingPurchasesParams.newBuilder().enableOneTimeProducts().build()
            )
            .enableAutoServiceReconnection()
            .build()

        connectToPlayBilling()
    }
    
    /**
     * 检查是否为模拟器
     */
    private fun isEmulator(): Boolean {
        return (android.os.Build.FINGERPRINT.startsWith("generic")
                || android.os.Build.FINGERPRINT.startsWith("unknown")
                || android.os.Build.MODEL.contains("google_sdk")
                || android.os.Build.MODEL.contains("Emulator")
                || android.os.Build.MODEL.contains("Android SDK built for x86")
                || android.os.Build.MANUFACTURER.contains("Genymotion")
                || (android.os.Build.BRAND.startsWith("generic") && android.os.Build.DEVICE.startsWith("generic"))
                || "google_sdk" == android.os.Build.PRODUCT)
    }

    fun release() {
      if (::billingClient.isInitialized) {
          billingClient.endConnection()
          isConnected = false
          EasyLog.log("BillingRepository - BillingClient 资源已释放")
      }
      // 清理待处理的购买请求
      pendingPurchaseProductId = null
      // 取消协程作用域
      eventScope.cancel()
    }
    
    private fun connectToPlayBilling() {
        billingClient.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(billingResult: BillingResult) {
                this@BillingRepository.onBillingSetupFinished(billingResult)
            }

            override fun onBillingServiceDisconnected() {
                this@BillingRepository.onBillingServiceDisconnected()
            }
        })
    }

    override fun onPurchasesUpdated(billingResult: BillingResult, purchases: MutableList<Purchase>?) {
        EasyLog.log("BillingRepository - 购买更新回调: 响应码=${billingResult.responseCode}")
        
        when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                if (purchases != null && purchases.isNotEmpty()) {
                    EasyLog.log("BillingRepository - 购买成功，处理 ${purchases.size} 个购买")
                    for (purchase in purchases) {
                        handlePurchase(purchase)
                        // 发送购买成功事件
                        eventScope.launch {
                            _eventFlow.emit(BillingEvent.PurchaseSuccess(purchase))
                        }
                    }
                } else {
                    EasyLog.log("BillingRepository - 购买成功但购买列表为空")
                }
            }
            BillingClient.BillingResponseCode.USER_CANCELED -> {
                EasyLog.log("BillingRepository - 用户取消购买")
                // 用户取消不发送失败事件
            }
            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                EasyLog.log("BillingRepository - 商品已拥有: 用户已经拥有该订阅")
                // 发送购买失败事件
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, "商品已拥有"))
                }
            }
            BillingClient.BillingResponseCode.ITEM_NOT_OWNED -> {
                EasyLog.log("BillingRepository - 商品未拥有: 用户未购买该商品")
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, "商品未拥有"))
                }
            }
            BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                EasyLog.log("BillingRepository - 商品不可用: 商品在当前地区不可用")
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, "商品在当前地区不可用"))
                }
            }
            BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                EasyLog.log("BillingRepository - 开发者错误: 请检查商品ID配置、应用签名、测试用户设置")
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, "开发者错误"))
                }
            }
            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                EasyLog.log("BillingRepository - 服务不可用: Google Play 服务暂时不可用")
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, "服务不可用"))
                }
            }
            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                EasyLog.log("BillingRepository - 计费不可用: 设备不支持 Google Play 计费")
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, "设备不支持 Google Play 计费"))
                }
            }
            BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                EasyLog.log("BillingRepository - 网络错误: 网络连接问题")
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, "网络错误"))
                }
            }
            BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                EasyLog.log("BillingRepository - 功能不支持: 当前设备不支持此功能")
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, "功能不支持"))
                }
            }
            BillingClient.BillingResponseCode.ERROR -> {
                EasyLog.log("BillingRepository - 一般错误: 发生了未知错误")
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, "一般错误"))
                }
            }
            else -> {
                EasyLog.log("BillingRepository - 购买失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})")
                eventScope.launch {
                    _eventFlow.emit(BillingEvent.PurchaseFailed(billingResult.responseCode, billingResult.debugMessage ?: "未知错误"))
                }
            }
        }
    }

    // 保存待处理的购买请求（仅产品ID，不持有Activity）
    private var pendingPurchaseProductId: String? = null
    
    override fun onBillingSetupFinished(billingResult: BillingResult) {
        EasyLog.log("BillingRepository - BillingClient 连接结果: 响应码=${billingResult.responseCode}")
        EasyLog.log("BillingRepository - 连接详情: ${billingResult.debugMessage}")
        
        if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
            isConnected = true
            EasyLog.log("BillingRepository - BillingClient 连接成功")
            
            // 发送连接成功事件
            eventScope.launch {
                _eventFlow.emit(BillingEvent.Connected)
            }

            // 连接成功后，如果 plansFlow 有数据则查询价格，否则等待 fetchRemote 完成
            val currentPlans = _plansFlow.value
            if (currentPlans.isNotEmpty()) {
                EasyLog.log("BillingRepository - plansFlow 已有数据，立即查询价格")
                querySkuDetails()
            } else {
                EasyLog.log("BillingRepository - plansFlow 为空，等待 fetchRemote 完成后再查询价格")
            }
        } else {
            EasyLog.log("BillingRepository - BillingClient 连接失败: ${billingResult.debugMessage}")
            EasyLog.log("BillingRepository - 连接失败响应码: ${billingResult.responseCode}")

            // 连接失败时，尝试重新连接（自动重连机制）
            eventScope.launch {
                kotlinx.coroutines.delay(5000) // 等待5秒后重连
                if (!isConnected) {
                    EasyLog.log("BillingRepository - 尝试重新连接 BillingClient")
                    connectToPlayBilling()
                }
            }
        }
    }

    override fun onBillingServiceDisconnected() {
        isConnected = false
        EasyLog.log("BillingRepository - BillingClient 断开连接")
        
        // 发送断开连接事件
        eventScope.launch {
            _eventFlow.emit(BillingEvent.Disconnected)
        }

        // 自动重连机制
        eventScope.launch {
            kotlinx.coroutines.delay(1000) // 等待1秒后重连
            if (!isConnected) {
                EasyLog.log("BillingRepository - 自动重连 BillingClient")
                connectToPlayBilling()
            }
        }
    }    
  
    suspend fun fetchRemote() {
      runCatching { api.getSubscriptionPlans() }
        .onSuccess { result ->
          when (result) {
            is HttpResult.Success -> {
              val response = result.data
              val currentSubscription = response.currentSubscription
              
              // 根据currentSubscription是否为空判断会员状态
              val isSubscribed = currentSubscription != null
              val subscriptionId = currentSubscription?.planId
              val purchaseTime = currentSubscription?.startDate?.let { 
                try { it.toLong() } catch (e: Exception) { 0L } 
              } ?: 0L
              val expiryTime = currentSubscription?.endDate?.let { 
                try { it.toLong() } catch (e: Exception) { 0L } 
              } ?: 0L
              
              val vipStatus = VipStatus(
                isSubscribed = isSubscribed,
                subscriptionId = subscriptionId,
                purchaseTime = purchaseTime,
                expiryTime = expiryTime
              )
              
              EasyLog.log("会员状态更新: isSubscribed=$isSubscribed, subscriptionId=$subscriptionId")
              saveLocalVipStatus(vipStatus)
              _vipStatusFlow.value = vipStatus
              
              // 更新订阅计划列表
              val vipPlans = response.plans.map { plan ->
                VipPlan(
                  googleProductId = plan.googlePlayProductId,
                  discountRate = plan.discountRate,
                  name = plan.name,
                  planType = plan.planType,
                  description = plan.description
                )
              }
              EasyLog.log("订阅计划更新: 获取到 ${vipPlans.size} 个计划")
              
              // 检查是否有实际变化
              val currentPlans = _plansFlow.value
              val hasChanges = checkPlansChanged(currentPlans, vipPlans)
              
              if (hasChanges) {
                EasyLog.log("检测到计划数据变化，更新 plansFlow")
                saveLocalPlans(vipPlans)
                _plansFlow.value = vipPlans

                  // 如果 BillingClient 已连接，立即查询价格
                  if (isConnected) {
                      EasyLog.log("BillingClient 已连接，立即查询价格信息")
                      querySkuDetails()
                  } else {
                      EasyLog.log("BillingClient 未连接，等待连接成功后查询价格")
                  }
              } else {
                EasyLog.log("计划数据无变化，跳过更新")

                  // 即使数据无变化，如果 BillingClient 已连接且 plansFlow 为空，也要查询价格
                  if (isConnected && _plansFlow.value.isEmpty()) {
                      EasyLog.log("plansFlow 为空但 BillingClient 已连接，查询价格信息")
                      querySkuDetails()
                  }
              }
            }
            is HttpResult.Failure -> {
              EasyLog.log("获取订阅计划失败: ${result.message}")
            }
          }
        }
        .onFailure { exception ->
          when (exception) {
            is kotlinx.coroutines.CancellationException -> {
              EasyLog.log("获取订阅计划被取消: ${exception.message}")
              // 协程被取消是正常情况，不需要特殊处理
            }
            else -> {
              EasyLog.log("获取订阅计划异常: ${exception.message}")
            }
          }
        }
    }
    
    private fun querySkuDetails() {
        // 检查BillingClient连接状态
        if (!isConnected) {
            EasyLog.log("BillingRepository - BillingClient 未连接，无法查询商品")
            return
        }
        
        // 从 plansFlow 获取商品ID列表
        val currentPlans = _plansFlow.value
        if (currentPlans.isEmpty()) {
            EasyLog.log("BillingRepository - plansFlow 为空，跳过价格查询")
            return
        }
        
        val subscriptionIds = currentPlans.map { it.googleProductId }
        EasyLog.log("BillingRepository - 从 plansFlow 获取商品ID: $subscriptionIds")
        EasyLog.log("BillingRepository - 当前设备信息:")
        EasyLog.log("  制造商: ${android.os.Build.MANUFACTURER}")
        EasyLog.log("  型号: ${android.os.Build.MODEL}")
        EasyLog.log("  Android 版本: ${android.os.Build.VERSION.RELEASE}")
        EasyLog.log("  API 级别: ${android.os.Build.VERSION.SDK_INT}")
        EasyLog.log("  是否模拟器: ${isEmulator()}")
        
        // 使用新的 ProductDetails API
        val products = subscriptionIds.map { productId ->
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(productId)
                .setProductType(BillingClient.ProductType.SUBS)
                .build()
        }

        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(products)
            .build()

        EasyLog.log("BillingRepository - 发送查询请求到Google Play (新API)")
        EasyLog.log("BillingRepository - 查询参数: $subscriptionIds")
        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsResult ->
            EasyLog.log("BillingRepository - Google Play 查询结果: 响应码=${billingResult.responseCode}")
            EasyLog.log("BillingRepository - 查询结果详情: ${billingResult.debugMessage}")
            
            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    productDetailsResult?.productDetailsList?.let { detailsList ->
                        if (detailsList.isNotEmpty()) {
                            EasyLog.log("BillingRepository - 查询成功，获取到 ${detailsList.size} 个商品信息")
                            // 使用新的 ProductDetails 更新计划价格
                            updatePlansWithProductDetails(currentPlans, detailsList)
                        } else {
                            EasyLog.log("BillingRepository - 查询成功但返回空商品列表，可能原因: 商品ID不存在或未在Google Play Console中激活")
                        }
                    } ?: run {
                        EasyLog.log("BillingRepository - Google Play返回的商品列表为null")
                    }
                }
                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    EasyLog.log("BillingRepository - 开发者错误 (12): 请检查商品ID配置、应用签名、测试用户设置")
                    EasyLog.log("BillingRepository - 当前查询的商品ID: $subscriptionIds")
                    eventScope.launch {
                        _eventFlow.emit(BillingEvent.SkuDetailsQueryFailed(billingResult.responseCode, "开发者错误"))
                    }
                }
                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    EasyLog.log("BillingRepository - 服务不可用: Google Play 服务暂时不可用")
                }
                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    EasyLog.log("BillingRepository - 计费不可用: 设备不支持 Google Play 计费")
                }
                BillingClient.BillingResponseCode.ITEM_NOT_OWNED -> {
                    EasyLog.log("BillingRepository - 商品未拥有: 用户未购买该商品")
                }
                BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                    EasyLog.log("BillingRepository - 商品不可用: 商品在当前地区不可用")
                }
                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    EasyLog.log("BillingRepository - 网络错误: 网络连接问题")
                }
                BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                    EasyLog.log("BillingRepository - 功能不支持: 当前设备不支持此功能")
                }
                BillingClient.BillingResponseCode.USER_CANCELED -> {
                    EasyLog.log("BillingRepository - 用户取消: 用户取消了操作")
                }
                BillingClient.BillingResponseCode.ERROR -> {
                    EasyLog.log("BillingRepository - 一般错误: 发生了未知错误")
                }
                else -> {
                    EasyLog.log("BillingRepository - 未知错误: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})")
                }
            }
        }
    }

    // private fun queryPurchases() {
    //     billingClient.queryPurchasesAsync(
    //         QueryPurchasesParams.newBuilder()
    //             .setProductType(BillingClient.ProductType.SUBS)
    //             .build()
    //     ) { billingResult, purchasesList ->
    //         if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
    //             handlePurchases(purchasesList)
    //         }
    //     }
    // }

    // private fun handlePurchases(purchases: List<Purchase>) {
    //     if (purchases.isEmpty()) {
    //         // 更新会员状态为未订阅
    //         val newStatus = VipStatus(isSubscribed = false)
    //         _vipStatusFlow.value = newStatus
    //         saveLocalVipStatus(newStatus)
    //         return
    //     }

    //     for (purchase in purchases) {
    //         if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
    //             if (!purchase.isAcknowledged) {
    //                 acknowledgePurchase(purchase)
    //             }
    //             // 更新会员状态为已订阅
    //             val newStatus = VipStatus(
    //                 isSubscribed = true,
    //                 subscriptionId = purchase.products.firstOrNull(),
    //                 purchaseTime = purchase.purchaseTime,
    //                 expiryTime = 0L // 需要从服务器获取过期时间
    //             )
    //             _vipStatusFlow.value = newStatus
    //             saveLocalVipStatus(newStatus)
    //         }
    //     }
    // }

    private fun handlePurchase(purchase: Purchase) {
        if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
            if (!purchase.isAcknowledged) {
                acknowledgePurchase(purchase)
            }
            // 更新会员状态为已订阅
            val newStatus = VipStatus(
                isSubscribed = true,
                subscriptionId = purchase.products.firstOrNull(),
                purchaseTime = purchase.purchaseTime,
                expiryTime = 0L // 需要从服务器获取过期时间
            )
            _vipStatusFlow.value = newStatus
            saveLocalVipStatus(newStatus)
        }
    }

    private fun acknowledgePurchase(purchase: Purchase) {
        val acknowledgePurchaseParams = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()
        billingClient.acknowledgePurchase(acknowledgePurchaseParams) { billingResult ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                EasyLog.log("BillingRepository - 购买确认成功")
            }
        }
    }
    
    /**
     * 主动更新计划价格
     */
    fun updatePlansPrices() {
        EasyLog.log("=== 主动更新计划价格开始 ===")
        
        // 1. 检查连接状态
        if (!isConnected) {
            EasyLog.log("❌ BillingClient 未连接，无法查询价格")
            EasyLog.log("=== 主动更新计划价格结束 ===")
            return
        }
        
        // 2. 获取当前计划列表
        val currentPlans = _plansFlow.value
        if (currentPlans.isEmpty()) {
            EasyLog.log("⚠️ 本地计划列表为空，跳过价格更新")
            EasyLog.log("=== 主动更新计划价格结束 ===")
            return
        }
        
        // 3. 提取商品ID列表
        val productIds = currentPlans.map { it.googleProductId }
        EasyLog.log("准备查询商品价格，商品ID: $productIds")
        
        // 4. 使用新的 ProductDetails API 查询Google Play获取最新价格
        val products = productIds.map { productId ->
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(productId)
                .setProductType(BillingClient.ProductType.SUBS)
                .build()
        }

        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(products)
            .build()

        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsResult ->
            EasyLog.log("Google Play 价格查询结果: 响应码=${billingResult.responseCode}")
            
            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    productDetailsResult?.productDetailsList?.let { detailsList ->
                        if (detailsList.isNotEmpty()) {
                            // 5. 比较并更新价格
                            updatePlansWithProductDetails(currentPlans, detailsList)
                        } else {
                            EasyLog.log("Google Play返回空的价格列表")
                        }
                    } ?: run {
                        EasyLog.log("Google Play返回的价格列表为null")
                    }
                }
                else -> {
                    EasyLog.log("Google Play价格查询失败: ${billingResult.debugMessage}")
                }
            }
            EasyLog.log("=== 主动更新计划价格结束 ===")
        }
    }
    
    /**
     * 根据ProductDetails更新计划价格（新API方法）
     */
    private fun updatePlansWithProductDetails(currentPlans: List<VipPlan>, productDetailsList: List<ProductDetails>) {
        val updatedPlans = currentPlans.toMutableList()
        var updatedCount = 0
        
        EasyLog.log("开始比较价格信息 (新API)...")
        
        productDetailsList.forEach { productDetails ->
            val planId = productDetails.productId
            val index = updatedPlans.indexOfFirst { it.googleProductId == planId }
            
            if (index >= 0) {
                val currentPlan = updatedPlans[index]
                
                // 从 ProductDetails 中提取价格信息
                val offer = productDetails.subscriptionOfferDetails?.firstOrNull()
                val pricePhase = offer?.pricingPhases?.pricingPhaseList?.firstOrNull()
                
                if (pricePhase != null) {
                    val formattedPrice = pricePhase.formattedPrice
                    val currencyCode = pricePhase.priceCurrencyCode
                    val micros = pricePhase.priceAmountMicros
                    val correctedPrice = correctCurrencySymbol(formattedPrice, currencyCode)
                    
                    // 检查价格是否有变化
                    if (currentPlan.price != correctedPrice || 
                        currentPlan.currencyCode != currencyCode ||
                        currentPlan.priceAmountMicros != micros) {
                        
                        val oldPrice = currentPlan.price
                        updatedPlans[index] = currentPlan.copy(
                            price = correctedPrice,
                            originalPrice = correctedPrice,
                            currencyCode = currencyCode,
                            priceAmountMicros = micros
                        )
                        updatedCount++
                        
                        EasyLog.log("✅ 价格有变化，更新计划: $planId")
                        EasyLog.log("   计划名称: ${currentPlan.name}")
                        EasyLog.log("   价格变化: $oldPrice -> $correctedPrice")
                        EasyLog.log("   货币代码: ${currentPlan.currencyCode} -> $currencyCode")
                        EasyLog.log("   商品标题: ${productDetails.title}")
                        EasyLog.log("   商品描述: ${productDetails.description}")
                    } else {
                        EasyLog.log("ℹ️ 价格无变化，跳过: $planId (${currentPlan.name})")
                    }
                } else {
                    EasyLog.log("⚠️ 未找到价格信息: $planId")
                }
            } else {
                EasyLog.log("⚠️ 未找到匹配的计划ID: $planId")
            }
        }
        
        // 如果有变化，更新并通知
        if (updatedCount > 0) {
            EasyLog.log("✅ 检测到 $updatedCount 个计划价格变化，更新 plansFlow")
            _plansFlow.value = updatedPlans
            saveLocalPlans(updatedPlans) // 保存到本地缓存
        } else {
            EasyLog.log("ℹ️ 所有计划价格都无变化，无需更新")
        }
    }
    
    /**
     * 根据SkuDetails更新计划价格（旧API方法，保留兼容性）
     */
    private fun updatePlansWithSkuDetails(currentPlans: List<VipPlan>, skuDetails: List<SkuDetails>) {
        val updatedPlans = currentPlans.toMutableList()
        var updatedCount = 0
        
        EasyLog.log("开始比较价格信息...")
        
        skuDetails.forEach { sku ->
            val index = updatedPlans.indexOfFirst { it.googleProductId == sku.sku }
            if (index >= 0) {
                val currentPlan = updatedPlans[index]
                val correctedPrice = correctCurrencySymbol(sku.price, sku.priceCurrencyCode)
                
                // 检查价格是否有变化
                if (currentPlan.price != correctedPrice || 
                    currentPlan.currencyCode != sku.priceCurrencyCode ||
                    currentPlan.priceAmountMicros != sku.priceAmountMicros) {
                    
                    val oldPrice = currentPlan.price
                    updatedPlans[index] = currentPlan.copy(
                        price = correctedPrice,
                        originalPrice = correctedPrice,
                        currencyCode = sku.priceCurrencyCode,
                        priceAmountMicros = sku.priceAmountMicros
                    )
                    updatedCount++
                    
                    EasyLog.log("✅ 价格有变化，更新计划: ${sku.sku}")
                    EasyLog.log("   计划名称: ${currentPlan.name}")
                    EasyLog.log("   价格变化: $oldPrice -> $correctedPrice")
                    EasyLog.log("   货币代码: ${currentPlan.currencyCode} -> ${sku.priceCurrencyCode}")
                } else {
                    EasyLog.log("ℹ️ 价格无变化，跳过: ${sku.sku} (${currentPlan.name})")
                }
            } else {
                EasyLog.log("⚠️ 未找到匹配的计划ID: ${sku.sku}")
            }
        }
        
        // 6. 如果有变化，更新并通知
        if (updatedCount > 0) {
            EasyLog.log("✅ 检测到 $updatedCount 个计划价格变化，更新 plansFlow")
            _plansFlow.value = updatedPlans
            saveLocalPlans(updatedPlans) // 保存到本地缓存
        } else {
            EasyLog.log("ℹ️ 所有计划价格都无变化，无需更新")
        }
    }
    
    /**
     * 检查计划列表是否有关键字段变化
     */
    private fun checkPlansChanged(currentPlans: List<VipPlan>, newPlans: List<VipPlan>): Boolean {
        // 如果数量不同，肯定有变化
        if (currentPlans.size != newPlans.size) {
            EasyLog.log("计划数量变化: ${currentPlans.size} -> ${newPlans.size}")
            return true
        }
        
        // 逐个比较计划
        for (i in currentPlans.indices) {
            val current = currentPlans[i]
            val new = newPlans[i]
            
            // 检查关键字段是否变化
            if (current.googleProductId != new.googleProductId ||
                current.discountRate != new.discountRate ||
                current.planType != new.planType ||
                current.description != new.description) {
                
                EasyLog.log("检测到计划变化:")
                EasyLog.log("  googleProductId: ${current.googleProductId} -> ${new.googleProductId}")
                EasyLog.log("  discountRate: ${current.discountRate} -> ${new.discountRate}")
                EasyLog.log("  planType: ${current.planType} -> ${new.planType}")
                EasyLog.log("  description: ${current.description} -> ${new.description}")
                return true
            }
        }
        
        EasyLog.log("所有计划的关键字段都无变化")
        return false
    }
    
    /**
     * 检查购买前的状态
     */
    private fun checkPurchasePreconditions(activity: android.app.Activity): Boolean {
        if (!isConnected) {
            EasyLog.log("❌ BillingClient 未连接，无法启动购买流程")
            return false
        }
        
        // 检查 Google Play 服务是否可用
        val googleApiAvailability = com.google.android.gms.common.GoogleApiAvailability.getInstance()
        val context = activity.applicationContext
        val resultCode = googleApiAvailability.isGooglePlayServicesAvailable(context)
        
        EasyLog.log("Google Play 服务检查结果: $resultCode")
        
        when (resultCode) {
            com.google.android.gms.common.ConnectionResult.SUCCESS -> {
                EasyLog.log("✅ Google Play 服务可用")
            }
            com.google.android.gms.common.ConnectionResult.SERVICE_VERSION_UPDATE_REQUIRED -> {
                EasyLog.log("⚠️ Google Play 服务需要更新")
                // 尝试更新 Google Play 服务
                googleApiAvailability.getErrorDialog(activity, resultCode, 1001)?.show()
                return false
            }
            com.google.android.gms.common.ConnectionResult.SERVICE_DISABLED -> {
                EasyLog.log("❌ Google Play 服务被禁用")
                return false
            }
            com.google.android.gms.common.ConnectionResult.SERVICE_MISSING -> {
                EasyLog.log("❌ Google Play 服务未安装")
                return false
            }
            com.google.android.gms.common.ConnectionResult.SERVICE_INVALID -> {
                EasyLog.log("❌ Google Play 服务无效")
                return false
            }
            else -> {
                EasyLog.log("❌ Google Play 服务不可用: $resultCode")
                return false
            }
        }
        
        // 检查设备是否支持计费
        if (!isBillingSupported()) {
            EasyLog.log("❌ 设备不支持 Google Play 计费")
            return false
        }
        
        return true
    }
    
    /**
     * 检查设备是否支持计费
     */
    private fun isBillingSupported(): Boolean {
        return try {
            val billingResult = billingClient.isFeatureSupported(BillingClient.FeatureType.SUBSCRIPTIONS)
            val isSupported = billingResult.responseCode == BillingClient.BillingResponseCode.OK
            EasyLog.log("设备计费支持检查: $isSupported (响应码: ${billingResult.responseCode})")
            EasyLog.log("计费支持检查详情: ${billingResult.debugMessage}")
            isSupported
        } catch (e: Exception) {
            EasyLog.log("检查计费支持时出错: ${e.message}")
            EasyLog.log("异常堆栈: ${e.stackTraceToString()}")
            false
        }
    }
    
    /**
     * 检查是否已连接
     */
    fun isConnected(): Boolean = isConnected

    /**
     * 手动触发价格更新
     */
    fun refreshPrices() {
        EasyLog.log("手动触发价格更新")
        if (isConnected) {
            querySkuDetails()
        } else {
            EasyLog.log("BillingClient 未连接，无法更新价格")
        }
    }

    /**
     * 初始化并获取数据
     */
    suspend fun initializeAndFetch(context: Context) {
        // 1. 初始化 BillingClient
        initialize(context)

        // 2. 获取远程数据
        fetchRemote()

        // 3. 如果 BillingClient 已连接，查询价格
        if (isConnected) {
            querySkuDetails()
        }
    }
    
    /**
     * 启动购买流程
     */
    fun launchBillingFlow(activity: android.app.Activity, productId: String) {
        // 检查购买前条件
        if (!checkPurchasePreconditions(activity)) {
            return
        }
        
        EasyLog.log("开始启动购买流程，商品ID: $productId")
        
        // 检查连接状态
        if (!isConnected) {
            EasyLog.log("⚠️ BillingClient 未连接，无法启动购买流程")
            // 发送购买失败事件，让 UI 层处理重试逻辑
            eventScope.launch {
                _eventFlow.emit(BillingEvent.PurchaseFailed(-1, "BillingClient 未连接"))
            }
            return
        }
        
        // 执行购买流程
        launchBillingFlowInternal(activity, productId)
    }
    
    /**
     * 内部购买流程实现
     */
    private fun launchBillingFlowInternal(activity: android.app.Activity, productId: String) {
        // 先查询商品详情（使用新的 ProductDetails API）
        val product = QueryProductDetailsParams.Product.newBuilder()
            .setProductId(productId)
            .setProductType(BillingClient.ProductType.SUBS)
            .build()
            
        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(listOf(product))
            .build()

        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsResult ->
            EasyLog.log("BillingRepository - 查询商品详情结果: 响应码=${billingResult.responseCode}")
            
            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.OK -> {
                    productDetailsResult?.productDetailsList?.firstOrNull()?.let { productDetails ->
                        EasyLog.log("✅ 找到商品详情: ${productDetails.productId}")
                        EasyLog.log("   商品标题: ${productDetails.title}")
                        EasyLog.log("   商品描述: ${productDetails.description}")
                        
                        // 获取价格信息
                        val offer = productDetails.subscriptionOfferDetails?.firstOrNull()
                        val pricePhase = offer?.pricingPhases?.pricingPhaseList?.firstOrNull()
                        if (pricePhase != null) {
                            EasyLog.log("   价格: ${pricePhase.formattedPrice}")
                            EasyLog.log("   货币代码: ${pricePhase.priceCurrencyCode}")
                        }
                        
                        // 启动购买流程（使用新的 ProductDetails）
                        val billingFlowParams = BillingFlowParams.newBuilder()
                            .setProductDetailsParamsList(listOf(
                                BillingFlowParams.ProductDetailsParams.newBuilder()
                                    .setProductDetails(productDetails)
                                    .build()
                            ))
                            .build()
                            
                        val launchResult = billingClient.launchBillingFlow(activity, billingFlowParams)
                        EasyLog.log("✅ 购买流程启动结果: $launchResult")
                    } ?: run {
                        EasyLog.log("❌ 未找到商品详情: $productId")
                        EasyLog.log("可能原因:")
                        EasyLog.log("  1. 商品ID不存在于Google Play Console")
                        EasyLog.log("  2. 商品未激活或未发布")
                        EasyLog.log("  3. 应用签名与Google Play Console不匹配")
                        EasyLog.log("  4. 测试用户未正确设置")
                    }
                }
                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    EasyLog.log("❌ 开发者错误 (12): 请检查商品ID配置、应用签名、测试用户设置")
                    EasyLog.log("当前查询的商品ID: $productId")
                }
                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    EasyLog.log("❌ 服务不可用: Google Play 服务暂时不可用")
                }
                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    EasyLog.log("❌ 计费不可用: 设备不支持 Google Play 计费")
                }
                BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                    EasyLog.log("❌ 商品不可用: 商品在当前地区不可用")
                }
                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    EasyLog.log("❌ 网络错误: 网络连接问题")
                }
                else -> {
                    EasyLog.log("❌ 查询商品详情失败: ${billingResult.debugMessage} (错误码: ${billingResult.responseCode})")
                }
            }
        }
    }
    
    /**
     * 根据货币代码修正货币符号
     */
    private fun correctCurrencySymbol(price: String, currencyCode: String): String {
        val numberPart = price.filter { it.isDigit() || it == '.' }
        
        return when (currencyCode) {
            "TWD" -> "NT$$numberPart"
            "USD" -> "$$numberPart"
            "EUR" -> "€$numberPart"
            "JPY" -> "¥$numberPart"
            "CNY" -> "¥$numberPart"
            "GBP" -> "£$numberPart"
            "KRW" -> "₩$numberPart"
            "SGD" -> "S$$numberPart"
            "HKD" -> "HK$$numberPart"
            else -> price // 如果不知道货币代码，保持原样
        }
    }
  
    // suspend fun updateOnServer(profile: UserProfile) {
    //   runCatching { api.updateUserProfile(profile) }
    //     .onSuccess {
    //       saveLocal(profile)
    //       _profileFlow.value = profile
    //     }
    //     .onFailure { /* 可以给 UI 报错提示 */ }
    // }
  
    private fun saveLocalVipStatus(vipStatus: VipStatus) {
      val json = MoshiUtils.toJson(vipStatus)
      IntySetting.setUserProfileData("vip_status", json)
    }
  
    private fun getLocalVipStatus(): VipStatus {
      val vipStatusStr = IntySetting.getUserProfileData("vip_status")
      return if (vipStatusStr.isNullOrEmpty()) {
        VipStatus(isSubscribed = false)
      } else {
        try {
          MoshiUtils.fromJson<VipStatus>(vipStatusStr) ?: VipStatus(isSubscribed = false)
        } catch (e: Exception) {
          EasyLog.log("解析本地会员状态失败: ${e.message}")
          VipStatus(isSubscribed = false)
        }
      }
    }
    
    private fun saveLocalPlans(plans: List<VipPlan>) {
      try {
        val type = com.squareup.moshi.Types.newParameterizedType(
          List::class.java, 
          VipPlan::class.java
        )
        val adapter = MoshiUtils.moshiBuild.adapter<List<VipPlan>>(type)
        val json = adapter.toJson(plans) ?: ""
        IntySetting.setUserProfileData("subscription_plans", json)
      } catch (e: Exception) {
        EasyLog.log("保存本地订阅计划失败: ${e.message}")
        EasyLog.log("错误详情: ${e.stackTraceToString()}")
      }
    }
    
    private fun getLocalPlans(): List<VipPlan> {
      val plansStr = IntySetting.getUserProfileData("subscription_plans")
      return if (plansStr.isNullOrEmpty()) {
        emptyList()
      } else {
        try {
          val type = com.squareup.moshi.Types.newParameterizedType(
            List::class.java, 
            VipPlan::class.java
          )
          val adapter = MoshiUtils.moshiBuild.adapter<List<VipPlan>>(type)
          adapter.fromJson(plansStr) ?: emptyList()
        } catch (e: Exception) {
          EasyLog.log("解析本地订阅计划失败: ${e.message}")
          EasyLog.log("错误详情: ${e.stackTraceToString()}")
          
          // 如果解析失败，清除损坏的缓存数据
          try {
            IntySetting.setUserProfileData("subscription_plans", "")
            EasyLog.log("已清除损坏的订阅计划缓存数据")
          } catch (clearException: Exception) {
            EasyLog.log("清除缓存数据失败: ${clearException.message}")
          }
          
          emptyList()
        }
      }
    }
}