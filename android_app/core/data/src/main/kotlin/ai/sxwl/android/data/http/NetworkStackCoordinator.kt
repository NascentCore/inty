package ai.sxwl.android.data.http

import android.app.Application

/**
 * 统一网络栈协调入口。
 *
 * Phase 2 迁移步骤中，我们把 app 模块对 `IntyNetworkManager` 的直接引用迁出到 core/data，
 * app 只通过该协调器完成初始化与缓存清理，避免继续耦合 Stainless SDK 细节。
 */
object NetworkStackCoordinator {
    fun initialize(application: Application, buildType: String) {
        IntyNetworkManager.initialize(application, buildType = buildType)
    }

    fun clearAllRuntimeCaches() {
        IntyNetworkManager.clearClientCache()
        ai.sxwl.android.data.api.NetServiceMgr.clearCache()
    }
}
