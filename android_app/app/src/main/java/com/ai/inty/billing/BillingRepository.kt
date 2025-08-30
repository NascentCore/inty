package com.ai.inty.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PurchasesUpdatedListener
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 计费仓库主类
 */
object BillingRepository : PurchasesUpdatedListener, BillingClientStateListener {
    private lateinit var billingClient: BillingClient
    private var isConnected = false

    // 协程作用域，用于发送事件
    private val eventScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    private val _vipStatusFlow = MutableStateFlow<VipStatus>(VipStatus(isSubscribed = false))
    val vipStatusFlow: StateFlow<VipStatus> = _vipStatusFlow.asStateFlow()

    private val _plansFlow = MutableStateFlow<List<VipPlan>>(emptyList())
    val plansFlow: StateFlow<List<VipPlan>> = _plansFlow.asStateFlow()

    // 初始化状态Flow
    private val _initStateFlow = MutableStateFlow(BillingInitState())
    val initStateFlow: StateFlow<BillingInitState> = _initStateFlow.asStateFlow()

    // 事件流，用于通知 UI 层计费状态变化
    private val _eventFlow = MutableSharedFlow<BillingEvent>()
    val eventFlow: SharedFlow<BillingEvent> = _eventFlow.asSharedFlow()

    // 子管理器
    private lateinit var priceManager: BillingPriceManager
    private lateinit var purchaseManager: BillingPurchaseManager
    private lateinit var remoteManager: BillingRemoteManager

    init {
        // 应用启动先读本地
        _vipStatusFlow.value = BillingStorage.getLocalVipStatus()
        _plansFlow.value = BillingStorage.getLocalPlans()
    }

    /**
     * 初始化 BillingClient
     */
    fun initialize(context: Context) {
        if (::billingClient.isInitialized) return

        // 打印设备区域和货币信息
        val locale = context.resources.configuration.locales[0]
        val currency = java.util.Currency.getInstance(locale)
        EasyLog.log("BillingRepository - 设备区域: ${locale.displayCountry} (${locale.country}), 货币: ${currency.displayName} (${currency.currencyCode})")

        // 检查设备信息
        EasyLog.log("BillingRepository - 设备信息:")
        EasyLog.log("BillingRepository  制造商: ${android.os.Build.MANUFACTURER}")
        EasyLog.log("BillingRepository  型号: ${android.os.Build.MODEL}")
        EasyLog.log("BillingRepository  Android 版本: ${android.os.Build.VERSION.RELEASE}")
        EasyLog.log("BillingRepository  API 级别: ${android.os.Build.VERSION.SDK_INT}")
        EasyLog.log("BillingRepository  是否模拟器: ${BillingUtils.isEmulator()}")

        // 预检查Google Play服务
        val hasGooglePlayServices = BillingUtils.isGooglePlayServicesAvailable(context)
        _initStateFlow.value =
            _initStateFlow.value.copy(hasGooglePlayServices = hasGooglePlayServices)

        if (!hasGooglePlayServices) {
            EasyLog.log("BillingRepository - Google Play 服务不可用，跳过BillingClient初始化")
            _initStateFlow.value = _initStateFlow.value.copy(
                errorMessage = "Google Play 服务不可用"
            )
            eventScope.launch {
                _eventFlow.emit(BillingEvent.InitializationFailed("Google Play 服务不可用"))
            }
            return
        }

        billingClient = BillingClient.newBuilder(context.applicationContext)
            .setListener(this)
            .enablePendingPurchases()
            .build()

        // 初始化子管理器
        priceManager = BillingPriceManager(billingClient, eventScope, _eventFlow, _plansFlow)
        purchaseManager =
            BillingPurchaseManager(billingClient, eventScope, _eventFlow, _vipStatusFlow)
        remoteManager = BillingRemoteManager(_vipStatusFlow, _plansFlow, priceManager)

        connectToPlayBilling()
    }

    fun release() {
        if (::billingClient.isInitialized) {
            billingClient.endConnection()
            isConnected = false
            EasyLog.log("BillingRepository - BillingClient 资源已释放")
        }
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

    override fun onPurchasesUpdated(
        billingResult: BillingResult,
        purchases: MutableList<com.android.billingclient.api.Purchase>?,
    ) {
        purchaseManager.onPurchasesUpdated(billingResult, purchases)
        EasyLog.log(
            "BillingRepository 购买结果onPurchasesUpdated $billingResult, $purchases ",
            EasyLog.INFO
        )
    }

    override fun onBillingSetupFinished(billingResult: BillingResult) {
        EasyLog.log("BillingRepository - BillingClient 连接结果: 响应码=${billingResult.responseCode}")
        EasyLog.log("BillingRepository - 连接详情: ${billingResult.debugMessage}")

        if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
            isConnected = true
            EasyLog.log("BillingRepository - BillingClient 连接成功 isReady:${billingClient.isReady} ,, connectState: ${billingClient.connectionState}")

            // 更新初始化状态
            _initStateFlow.value = _initStateFlow.value.copy(
                isInitialized = true,
                isConnected = true,
                errorMessage = null
            )

            // 发送连接成功事件
            eventScope.launch {
                _eventFlow.emit(BillingEvent.Connected)
            }

            // 连接成功后，立即获取远程数据
            eventScope.launch {
                fetchRemote()
            }
        } else {
            EasyLog.log("BillingRepository - BillingClient 连接失败: ${billingResult.debugMessage}")
            EasyLog.log("BillingRepository - 连接失败响应码: ${billingResult.responseCode}")

            // 更新初始化状态
            _initStateFlow.value = _initStateFlow.value.copy(
                isInitialized = true,
                isConnected = false,
                errorMessage = "连接失败: ${billingResult.debugMessage}"
            )

            // 连接失败时，尝试重新连接（自动重连机制）
            eventScope.launch {
                delay(5000) // 等待5秒后重连
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
            delay(1000) // 等待1秒后重连
            if (!isConnected) {
                EasyLog.log("BillingRepository - 自动重连 BillingClient")
                connectToPlayBilling()
            }
        }
    }

    suspend fun fetchRemote() {
        if (!::remoteManager.isInitialized) {
            EasyLog.log("BillingRepository fetchRemote - remoteManager 未初始化，跳过远程数据获取")
            return
        }
        remoteManager.fetchRemote(isConnected)
    }

    /**
     * 检查是否已连接
     */
    fun isConnected(): Boolean = isConnected

    /**
     * 检查是否已初始化
     */
    fun isInitialized(): Boolean = ::billingClient.isInitialized

    /**
     * 获取BillingClient连接状态
     */
    fun getConnectionState(): String {
        return if (::billingClient.isInitialized) {
            when (billingClient.connectionState) {
                0 -> "DISCONNECTED (0)"
                1 -> "CONNECTING (1)"
                2 -> "CONNECTED (2) ✅"
                else -> "UNKNOWN (${billingClient.connectionState})"
            }
        } else {
            "NOT_INITIALIZED"
        }
    }

    /**
     * 手动触发价格更新
     */
    fun refreshPrices() {
        EasyLog.log("BillingRepository 手动触发价格更新")
        if (isConnected) {
            priceManager.querySkuDetails(isConnected)
        } else {
            EasyLog.log("BillingRepository BillingClient 未连接，无法更新价格")
        }
    }

    /**
     * 初始化并获取数据
     */
    suspend fun initializeAndFetch(context: Context) {
        // 1. 初始化 BillingClient
        initialize(context)

        // 2. 等待连接完成后再获取远程数据
        // fetchRemote() 会在 onBillingSetupFinished 中自动调用
    }

    /**
     * 启动购买流程
     */
    fun launchBillingFlow(activity: Activity, productId: String) {
        purchaseManager.launchBillingFlow(activity, productId)
    }

    /**
     * 增强的订阅状态监控
     */
    fun startEnhancedSubscriptionMonitoring() {
        eventScope.launch {
            _eventFlow.collect { event ->
                when (event) {
                    is BillingEvent.PurchaseSuccess -> {
                        EasyLog.log("BillingRepository - 购买成功，刷新状态")
                        delay(2000)
                        refreshSubscriptionStatus()
                    }

                    is BillingEvent.Connected -> {
                        EasyLog.log("BillingRepository - 连接成功，刷新状态")
                        refreshSubscriptionStatus()
                    }

                    is BillingEvent.AppResumed -> {
                        EasyLog.log("BillingRepository - 应用恢复，检查状态")
                        refreshSubscriptionStatus()
                    }

                    else -> {
                        // 其他事件不需要特殊处理
                    }
                }
            }
        }
    }

    /**
     * 监听订阅状态变化并自动刷新（保持向后兼容）
     */
    fun startSubscriptionStatusMonitoring() {
        startEnhancedSubscriptionMonitoring()
    }

    /**
     * 智能刷新订阅状态
     */
    fun refreshSubscriptionStatus() {
        eventScope.launch {
            try {
                EasyLog.log("BillingRepository - 开始刷新订阅状态")
                val oldStatus = _vipStatusFlow.value
                fetchRemote()

                // 检查状态是否发生变化
                val newStatus = _vipStatusFlow.value
                if (oldStatus.isSubscribed != newStatus.isSubscribed) {
                    EasyLog.log("BillingRepository - 订阅状态发生变化: ${oldStatus.isSubscribed} -> ${newStatus.isSubscribed}")
                    _eventFlow.emit(BillingEvent.SubscriptionStatusChanged(oldStatus, newStatus))
                }
            } catch (e: Exception) {
                EasyLog.log("BillingRepository - 刷新订阅状态失败: ${e.message}")
            }
        }
    }

    // ==================== 简化的公共API接口 ====================

    /**
     * 检查用户是否为VIP
     */
    fun isVip(): Boolean = vipStatusFlow.value.isSubscribed

    /**
     * 获取当前VIP状态
     */
    fun getVipStatus(): VipStatus = vipStatusFlow.value

    /**
     * 获取订阅计划列表
     */
    fun getPlans(): List<VipPlan> = plansFlow.value

    /**
     * 购买指定商品
     */
    fun purchase(activity: Activity, productId: String) {
        launchBillingFlow(activity, productId)
    }

    /**
     * 刷新状态
     */
    fun refresh() {
        refreshSubscriptionStatus()
    }

    /**
     * 通知应用恢复
     */
    fun notifyAppResumed() {
        eventScope.launch {
            _eventFlow.emit(BillingEvent.AppResumed)
        }
    }
}
