package ai.sxwl.android.data.http

import android.app.Application

/**
 * 统一网络栈协调入口。
 *
 * app 只通过该协调器完成网络层初始化与缓存清理，避免耦合底层实现细节。
 */
object NetworkStackCoordinator {
    fun initialize(application: Application, buildType: String) {
        ai.sxwl.android.data.http.config.NetworkConfig.setBuildType(buildType)
        NetworkStateManager.initialize(application)
    }

    fun clearAllRuntimeCaches() {
        ai.sxwl.android.data.api.NetServiceMgr.clearCache()
    }
}
