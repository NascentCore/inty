package com.ai.inty

import android.app.Application
import android.content.Context
import com.ai.inty.base.initImageLoader
import com.ai.inty.billing.BillingRepository
import com.ai.inty.netapi.IntyNetworkManager
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

        // 立即初始化网络管理器（轻量级，不阻塞）
        NetworkManager.getInstance().initialize(this)
        IntyNetworkManager.initialize(this)
        
        // 立即初始化统一启动管理器（只做必要的登录判断，不阻塞）
        UnifiedStartupManager.initializeEssential(this)

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
