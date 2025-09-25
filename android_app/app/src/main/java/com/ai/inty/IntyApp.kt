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

        EasyLog.defaultInit()
        initImageLoader()

        // 初始化网络管理器
        NetworkManager.getInstance().initialize(this)
        
        // 初始化新的 IntyNetworkManager
        IntyNetworkManager.initialize(this)

        // 初始化统一启动管理器
        UnifiedStartupManager.initialize(this)
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
