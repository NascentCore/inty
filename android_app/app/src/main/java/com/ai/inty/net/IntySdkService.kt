package com.ai.inty.net

import android.content.Context
import com.inty.api.client.IntyClient
import com.inty.api.client.okhttp.IntyOkHttpClient
import com.inty.utils.AppEnv
import com.inty.utils.storage.IntySetting
import com.therouter.inject.ServiceProvider
import okhttp3.OkHttpClient
import com.ai.inty.Constant

/**
 * Inty Kotlin SDK 服务管理器
 * 提供统一的 SDK 客户端配置和管理
 */
object IntySdkService {
    
    private var _client: IntyClient? = null
    
    /**
     * 获取配置好的 IntyClient 实例
     * 使用单例模式，避免重复创建客户端
     */
    val client: IntyClient
        get() {
            if (_client == null) {
                _client = createClient()
            }
            return _client!!
        }
    
    /**
     * 创建 IntyClient 实例
     * 使用 IntyOkHttpClient 的默认配置
     */
    private fun createClient(): IntyClient {
        return IntyOkHttpClient.builder()
            .apiKey(IntySetting.getCurToken())
            .baseUrl(getBaseUrl())
            .build()
    }
    
    /**
     * 获取基础 URL
     * 与现有网络服务保持一致的环境配置
     */
    private fun getBaseUrl(): String {
        return when (AppEnv.buildType) {
            "local" -> "http://${Constant.USER_HOST_LOCAL}/api/v1"
            "debug" -> "https://${Constant.USER_HOST_DEV}/api/v1"
            "playdebug" -> "https://${Constant.USER_HOST_DEV}/api/v1"
            "release" -> "https://${Constant.USER_HOST}/api/v1"
            else -> "https://${Constant.USER_HOST_DEV}/api/v1" // fallback to staging
        }
    }
    
    /**
     * 重置客户端
     * 当用户登录状态改变时调用，重新创建客户端
     */
    fun resetClient() {
        _client = null
    }
    
    /**
     * 获取异步客户端
     * 用于协程环境中的异步调用
     */
    fun getAsyncClient(): com.inty.api.client.IntyClientAsync {
        return com.inty.api.client.okhttp.IntyOkHttpClientAsync.builder()
            .apiKey(IntySetting.getCurToken())
            .baseUrl(getBaseUrl())
            .build()
    }
}

/**
 * 通过 TheRouter 提供 SDK 服务
 * 可以在任何地方通过依赖注入获取
 */
@ServiceProvider
fun getIntySdkService(): IntySdkService {
    return IntySdkService
}

/**
 * 获取 IntyClient 实例的便捷方法
 */
@ServiceProvider
fun getIntyClient(): IntyClient {
    return IntySdkService.client
}

/**
 * 获取异步 IntyClient 实例的便捷方法
 */
@ServiceProvider
fun getIntyClientAsync(): com.inty.api.client.IntyClientAsync {
    return IntySdkService.getAsyncClient()
}
