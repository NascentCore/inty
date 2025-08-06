package com.ai.inty.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
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
        EasyLog.log("  制造商: ${android.os.Build.MANUFACTURER}")
        EasyLog.log("  型号: ${android.os.Build.MODEL}")
        EasyLog.log("  Android 版本: ${android.os.Build.VERSION.RELEASE}")
        EasyLog.log("  API 级别: ${android.os.Build.VERSION.SDK_INT}")
        EasyLog.log("  是否模拟器: ${BillingUtils.isEmulator()}")

        billingClient = BillingClient.newBuilder(context.applicationContext)
            .setListener(this)
            .enablePendingPurchases(
                PendingPurchasesParams.newBuilder().enableOneTimeProducts().build()
            )
            .enableAutoServiceReconnection()
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
            EasyLog.log("BillingRepository - BillingClient 连接成功")

            // 发送连接成功事件
            eventScope.launch {
                _eventFlow.emit(BillingEvent.Connected)
            }

            // 连接成功后，如果 plansFlow 有数据则查询价格，否则等待 fetchRemote 完成
            val currentPlans = _plansFlow.value
            if (currentPlans.isNotEmpty()) {
                EasyLog.log("BillingRepository - plansFlow 已有数据，立即查询价格")
                priceManager.querySkuDetails(isConnected)
            } else {
                EasyLog.log("BillingRepository - plansFlow 为空，等待 fetchRemote 完成后再查询价格")
            }
        } else {
            EasyLog.log("BillingRepository - BillingClient 连接失败: ${billingResult.debugMessage}")
            EasyLog.log("BillingRepository - 连接失败响应码: ${billingResult.responseCode}")

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
        remoteManager.fetchRemote(isConnected)
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
            priceManager.querySkuDetails(isConnected)
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
            priceManager.querySkuDetails(isConnected)
        }
    }

    /**
     * 启动购买流程
     */
    fun launchBillingFlow(activity: Activity, productId: String) {
        purchaseManager.launchBillingFlow(activity, productId)
    }
}
