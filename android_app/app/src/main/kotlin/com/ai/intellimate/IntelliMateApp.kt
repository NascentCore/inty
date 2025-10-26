package com.ai.intellimate

import ai.sxwl.android.common.analytics.GlobalExceptionHandler
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import android.app.Application
import com.ai.intellimate.utils.NetworkManager
import com.ai.intellimate.utils.UnifiedStartupManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/** AppApplication的实现类 */
class IntelliMateApp : Application() {

    override fun onCreate() {
        super.onCreate()
// 立即初始化网络管理器（轻量级，不阻塞）
        NetworkManager.Companion.getInstance().initialize(this)
        IntyNetworkManager.initialize(this, buildType = BuildConfig.BUILD_TYPE)
// 立即初始化统一启动管理器（只做需要的登录判断，不阻塞）
        UnifiedStartupManager.initializeEssential(this)
// 记录应用启动事件
        FirebaseManager.logEvent("app_start")
//安装全局异常处理器
        GlobalExceptionHandler.Companion.install(this)
// 异步初始化所有可能阻塞的组件
        CoroutineScope(Dispatchers.IO).launch {
            try {
// 异步进行完整的数据预加载和缓存
                UnifiedStartupManager.initializeAsync(this@IntelliMateApp)
            } catch (e: Exception) {
                LogUtils.e("IntyApp - 异步初始化失败: ${e.message}")
            }
        }
    }

    override fun onTerminate() {
        super.onTerminate()
//应用退出时释放Billing连接
        if (BillingRepository.isInitialized()) {
            LogUtils.i("IntyApp - 应用退出，释放Billing连接")
            BillingRepository.release()
            FirebaseManager.logEvent("billing_release")
        }
    }
}
