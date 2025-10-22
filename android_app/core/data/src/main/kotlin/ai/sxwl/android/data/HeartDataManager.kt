package ai.sxwl.android.data

import ai.sxwl.android.data.store.DataStoreManager
import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

/**
 * 数据管理器
 * 为上层业务提供统一的数据访问入口
 * 遵循单向数据流原则，整合Repository和UseCase
 *
 * 职责：
 * 1. 统一数据访问接口
 * 2. 协调Repository和UseCase
 * 3. 提供响应式数据流
 * 4. 管理数据同步策略
 * 5. 网络状态检查和拦截
 *
 * 使用方式：
 * ```kotlin
 * // 获取实例
 * val dataManager = HeartDataManager
 * val userRepository = dataManager.getUserRepository()
 * ```
 */
object HeartDataManager {

    private var dataStore: DataStoreManager? = null

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /**
     * 需要在application中初始化
     * 注意：Utils工具类已通过androidx.startup自动初始化
     */
    fun initConfig(context: Context) {
        dataStore = dataStore ?: DataStoreManager(context)

    }

    /**
     * 获取DataStore管理器
     */
    fun getDataStore(): DataStoreManager? = dataStore


    /**
     * 更新网络请求的auth token
     */
    fun updateNetApiToken(token: String?) {

    }


}
