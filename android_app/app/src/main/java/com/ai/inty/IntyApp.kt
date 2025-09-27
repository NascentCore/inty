package com.ai.inty

import android.app.Application
import android.content.Context
import com.ai.inty.base.initImageLoader
import com.ai.inty.billing.BillingRepository
import com.ai.inty.netapi.IntyNetworkManager
import com.ai.inty.utils.FirebaseAnalyticsHelper
import com.ai.inty.utils.NetworkManager
import com.ai.inty.utils.UnifiedStartupManager
import com.inty.utils.AppEnv
import com.inty.utils.log.EasyLog
import com.inty.utils.log.defaultInit
import com.therouter.TheRouter
import kotlinx.coroutines.launch

/**
 * 应用Application的实现类
 */
class IntyApp : Application() {


    override fun attachBaseContext(base: Context?) {
        AppEnv.context = this
        AppEnv.DEBUG = BuildConfig.DEBUG
        AppEnv.buildType = BuildConfig.BUILD_TYPE
        AppEnv.testEnv = BuildConfig.DEBUG
        AppEnv.version_code = BuildConfig.VERSION_CODE
        AppEnv.version_name = BuildConfig.VERSION_NAME
        AppEnv.APPLICATION_ID = BuildConfig.APPLICATION_ID

        TheRouter.isDebug = BuildConfig.DEBUG

        super.attachBaseContext(base)
    }

    override fun onCreate() {
        super.onCreate()

        // 立即初始化日志，不阻塞
        EasyLog.defaultInit()

        // 立即初始化TheRouter（必须在其他组件之前）
        EasyLog.log("IntyApp - 开始初始化 TheRouter")
        TheRouter.init(this)
        EasyLog.log("IntyApp - TheRouter 初始化完成")
        
        // 配置 TheRouter 使用生成的服务提供者
        try {
            EasyLog.log("IntyApp - 开始配置 TheRouter 使用生成的服务提供者")
            // 手动调用服务提供者函数来注册它们
            val agentApi = com.ai.inty.net.getAgentApi()
            val chatApi = com.ai.inty.net.getChatApi()
            val commonApi = com.ai.inty.net.getCommonApi()
            val subscriptionApi = com.ai.inty.net.getSubscriptionApi()
            val userApi = com.ai.inty.net.getUserApi()
            
            // 手动注册到 TheRouter 服务容器
            TheRouter.inject(agentApi)
            TheRouter.inject(chatApi)
            TheRouter.inject(commonApi)
            TheRouter.inject(subscriptionApi)
            TheRouter.inject(userApi)
            
            EasyLog.log("IntyApp - 服务提供者手动注册到 TheRouter 完成")
        } catch (e: Exception) {
            EasyLog.log("IntyApp - 服务提供者手动注册到 TheRouter 失败: ${e.message}", EasyLog.ERROR)
        }
        
        // 测试 TheRouter 服务注册
        try {
            val testApi = TheRouter.get(com.ai.inty.net.IAgentApi::class.java)
            EasyLog.log("IntyApp - TheRouter 服务测试: IAgentApi = ${testApi != null}")
        } catch (e: Exception) {
            EasyLog.log("IntyApp - TheRouter 服务测试失败: ${e.message}", EasyLog.ERROR)
        }

        // 立即初始化网络管理器（轻量级，不阻塞）
        NetworkManager.getInstance().initialize(this)
        IntyNetworkManager.initialize(this)
        
        // 立即初始化统一启动管理器（只做必要的登录判断，不阻塞）
        UnifiedStartupManager.initializeEssential(this)
        
        // 初始化Firebase Analytics Helper
        FirebaseAnalyticsHelper.initialize(this)

        // 异步初始化所有可能阻塞的组件
        kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
            try {
                // 初始化图片加载器（可能阻塞）
                initImageLoader()
                
                // 异步进行完整的数据预加载和缓存
                UnifiedStartupManager.initializeAsync(this@IntyApp)
                
            } catch (e: Exception) {
                EasyLog.log("IntyApp - 异步初始化失败: ${e.message}", EasyLog.ERROR)
            }
        }
    }
    
    override fun onTerminate() {
        super.onTerminate()
        
        // 应用退出时释放Billing连接
        if (BillingRepository.isInitialized()) {
            EasyLog.log("IntyApp - 应用退出，释放Billing连接")
            BillingRepository.release()
        }
    }
}
