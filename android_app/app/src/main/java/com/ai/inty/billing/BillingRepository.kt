package com.ai.inty.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PurchasesUpdatedListener
import com.inty.utils.AppEnv
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

/** 计费仓库主类 */
object BillingRepository : PurchasesUpdatedListener, BillingClientStateListener {

    private const val DISCONNECT_RECONNECT_DELAY_MS = 1000L
    private const val TAG = "BillingRepository"

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

    /** 初始化 BillingClient */
    fun initialize(context: Context) {
        if (::billingClient.isInitialized) return

        logDeviceInfo(context)

        // 预检查Google Play服务
        val hasGooglePlayServices = BillingUtils.isGooglePlayServicesAvailable(context)
        updateInitState(hasGooglePlayServices = hasGooglePlayServices)

        if (!hasGooglePlayServices) {
            handleGooglePlayServicesUnavailable()
            return
        }

        initializeBillingClient(context)
        initializeManagers()
        connectToPlayBilling()
    }

    /** 记录设备信息 */
    private fun logDeviceInfo(context: Context) {
        val locale = context.resources.configuration.locales[0]
        val currency = java.util.Currency.getInstance(locale)
        log(
            "设备区域: ${locale.displayCountry} (${locale.country}), 货币: ${currency.displayName} (${currency.currencyCode})"
        )
        log(
            "设备信息: ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}, Android ${android.os.Build.VERSION.RELEASE}"
        )
        log("是否模拟器: ${BillingUtils.isEmulator()}")
    }

    /** 处理Google Play服务不可用的情况 */
    private fun handleGooglePlayServicesUnavailable() {
        log("Google Play 服务不可用，跳过BillingClient初始化")
        updateInitState(errorMessage = "Google Play 服务不可用")
        emitEvent(BillingEvent.InitializationFailed("Google Play 服务不可用"))
    }

    /** 初始化BillingClient */
    private fun initializeBillingClient(context: Context) {
        billingClient =
            BillingClient.newBuilder(context.applicationContext)
                .setListener(this)
                .enablePendingPurchases()
                .build()
    }

    /** 初始化子管理器 */
    private fun initializeManagers() {
        priceManager = BillingPriceManager(billingClient, eventScope, _eventFlow, _plansFlow)
        purchaseManager =
            BillingPurchaseManager(billingClient, eventScope, _eventFlow, _vipStatusFlow)
        remoteManager = BillingRemoteManager(_vipStatusFlow, _plansFlow, priceManager)
    }

    /** 更新初始化状态 */
    private fun updateInitState(
        isInitialized: Boolean = _initStateFlow.value.isInitialized,
        isConnected: Boolean = _initStateFlow.value.isConnected,
        hasGooglePlayServices: Boolean = _initStateFlow.value.hasGooglePlayServices,
        errorMessage: String? = _initStateFlow.value.errorMessage,
    ) {
        _initStateFlow.value =
            _initStateFlow.value.copy(
                isInitialized = isInitialized,
                isConnected = isConnected,
                hasGooglePlayServices = hasGooglePlayServices,
                errorMessage = errorMessage,
            )
    }

    /** 发送事件 */
    private fun emitEvent(event: BillingEvent) {
        eventScope.launch { _eventFlow.emit(event) }
    }

    /** 统一日志记录 */
    private fun log(message: String, level: Int = EasyLog.INFO) {
        EasyLog.log("$TAG - $message", level)
    }

    fun release() {
        if (::billingClient.isInitialized) {
            billingClient.endConnection()
            isConnected = false
            log("BillingClient 资源已释放")
        }
        // 取消协程作用域
        eventScope.cancel()
    }

    private fun connectToPlayBilling() {
        billingClient.startConnection(this)
    }

    override fun onPurchasesUpdated(
        billingResult: BillingResult,
        purchases: MutableList<com.android.billingclient.api.Purchase>?,
    ) {
        purchaseManager.onPurchasesUpdated(billingResult, purchases)
        log("购买结果onPurchasesUpdated $billingResult, $purchases", EasyLog.INFO)
    }

    override fun onBillingSetupFinished(billingResult: BillingResult) {
        log("BillingClient 连接结果: 响应码=${billingResult.responseCode}")
        log("连接详情: ${billingResult.debugMessage}")

        if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
            handleBillingSetupSuccess()
        } else {
            handleBillingSetupFailure(billingResult)
        }
    }

    /** 处理BillingClient连接成功 */
    private fun handleBillingSetupSuccess() {
        isConnected = true
        log(
            "BillingClient 连接成功 isReady:${billingClient.isReady}, connectState: ${billingClient.connectionState}"
        )

        // 更新初始化状态
        updateInitState(isInitialized = true, isConnected = true, errorMessage = null)

        // 发送连接成功事件
        emitEvent(BillingEvent.Connected)

        // 连接成功后，立即获取远程数据
        eventScope.launch { fetchRemote() }
    }

    /** 处理BillingClient连接失败 */
    private fun handleBillingSetupFailure(billingResult: BillingResult) {
        log("BillingClient 连接失败: ${billingResult.debugMessage}")
        log("连接失败响应码: ${billingResult.responseCode}")

        // 更新初始化状态
        updateInitState(
            isInitialized = true,
            isConnected = false,
            errorMessage = "连接失败: ${billingResult.debugMessage}",
        )

        // 连接失败时，尝试重新连接（自动重连机制）
        smartReconnect(billingResult)
    }

    override fun onBillingServiceDisconnected() {
        isConnected = false
        log("BillingClient 断开连接")

        // 发送断开连接事件
        emitEvent(BillingEvent.Disconnected)

        // 自动重连机制
        scheduleReconnect(DISCONNECT_RECONNECT_DELAY_MS)
    }

    /** 安排重连 */
    private fun scheduleReconnect(delayMs: Long) {
        eventScope.launch {
            delay(delayMs)
            if (!isConnected) {
                log("尝试重新连接 BillingClient")

                // 重新检查Google Play服务状态
                val context: Context? = AppEnv.context
                if (context != null && BillingUtils.isGooglePlayServicesAvailable(context)) {
                    log("Google Play 服务可用，尝试重新连接")
                    connectToPlayBilling()
                } else {
                    log("Google Play 服务仍不可用，跳过重连")
                    // 如果Google Play服务不可用，尝试强制重新检查
                    if (context != null) {
                        forceCheckGooglePlayServices(context)
                    }
                }
            }
        }
    }

    /** 智能重连：根据错误类型选择不同的重连策略 */
    private fun smartReconnect(billingResult: BillingResult) {
        val delayMs =
            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    log("服务不可用，使用较长延迟重连: 10秒")
                    10000L
                }

                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    log("网络错误，使用中等延迟重连: 5秒")
                    5000L
                }

                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    log("计费不可用，使用更长延迟重连: 30秒")
                    30000L // 增加到30秒，因为这种错误通常需要更长时间恢复
                }

                else -> {
                    log("其他错误，使用标准延迟重连: 5秒")
                    5000L
                }
            }

        scheduleReconnect(delayMs)
    }

    suspend fun fetchRemote() {
        if (!::remoteManager.isInitialized) {
            log("remoteManager 未初始化，跳过远程数据获取")
            return
        }
        remoteManager.fetchRemote(isConnected)
    }

    /** 检查是否已连接 */
    fun isConnected(): Boolean {
        // 双重检查：既检查内部状态，也检查BillingClient实际状态
        val internalConnected = isConnected
        val clientConnected =
            if (::billingClient.isInitialized) {
                billingClient.connectionState == BillingClient.ConnectionState.CONNECTED
            } else {
                false
            }

        // 如果状态不一致，同步状态
        if (internalConnected != clientConnected) {
            log("状态不一致检测到: internalConnected=$internalConnected, clientConnected=$clientConnected")
            isConnected = clientConnected
        }

        return isConnected
    }

    /** 检查是否已初始化 */
    fun isInitialized(): Boolean = ::billingClient.isInitialized

    /** 强制重新检查Google Play服务状态 */
    fun forceCheckGooglePlayServices(context: Context): Boolean {
        log("强制重新检查Google Play服务状态")
        val hasGooglePlayServices = BillingUtils.isGooglePlayServicesAvailable(context)
        updateInitState(hasGooglePlayServices = hasGooglePlayServices)

        if (!hasGooglePlayServices) {
            handleGooglePlayServicesUnavailable()
            return false
        }

        return true
    }

    /** 启动购买流程 */
    fun launchBillingFlow(activity: Activity, productId: String) {
        purchaseManager.launchBillingFlow(activity, productId)
    }

    /** 增强的订阅状态监控 */
    fun startEnhancedSubscriptionMonitoring() {
        eventScope.launch {
            _eventFlow.collect { event ->
                when (event) {
                    is BillingEvent.PurchaseSuccess -> {
                        log("购买成功，延迟刷新状态")
                        // 延迟刷新，等待服务器处理完成
                        delay(1000)
                        refreshSubscriptionStatus()
                    }

                    is BillingEvent.Connected -> {
                        log("连接成功，刷新状态")
                        refreshSubscriptionStatus()
                    }

                    is BillingEvent.AppResumed -> {
                        log("应用恢复，检查状态")
                        refreshSubscriptionStatus()
                    }

                    else -> log("未处理事件: $event")
                }
            }
        }
    }

    /** 智能刷新订阅状态 */
    fun refreshSubscriptionStatus() {
        eventScope.launch {
            try {
                log("开始刷新订阅状态")
                val oldStatus = _vipStatusFlow.value
                fetchRemote()

                // 检查状态是否发生变化
                val newStatus = _vipStatusFlow.value
                if (oldStatus.isSubscribed != newStatus.isSubscribed) {
                    log("订阅状态发生变化: ${oldStatus.isSubscribed} -> ${newStatus.isSubscribed}")
                    _eventFlow.emit(BillingEvent.SubscriptionStatusChanged(oldStatus, newStatus))
                }
            } catch (e: Exception) {
                log("刷新订阅状态失败: ${e.message}")
            }
        }
    }

    /** 通知应用恢复 */
    fun notifyAppResumed() {
        emitEvent(BillingEvent.AppResumed)
    }
}
