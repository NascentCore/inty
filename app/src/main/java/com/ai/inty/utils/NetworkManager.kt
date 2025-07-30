package com.ai.inty.utils

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.util.Log
import androidx.core.content.getSystemService
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.distinctUntilChanged

/**
 * 网络管理工具类
 *
 * 主要功能：
 * 1. 判断网络连接状态
 * 2. 监控网络状态变化
 * 3. 提供网络恢复后的回调机制
 */
class NetworkManager private constructor() {

    companion object {
        private const val TAG = "NetworkManager"

        @Volatile
        private var INSTANCE: NetworkManager? = null

        fun getInstance(): NetworkManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: NetworkManager().also { INSTANCE = it }
            }
        }
    }

    private var connectivityManager: ConnectivityManager? = null
    private var applicationContext: Context? = null
    private val networkCallbacks = mutableListOf<NetworkCallback>()
    private val networkStateListeners = mutableListOf<NetworkStateListener>()

    /**
     * 网络状态监听器接口
     */
    interface NetworkStateListener {
        /**
         * 网络状态变化回调
         * @param isConnected 是否已连接网络
         * @param networkType 网络类型
         */
        fun onNetworkStateChanged(isConnected: Boolean, networkType: NetworkType)

        /**
         * 网络恢复回调
         * 当网络从断开状态恢复到连接状态时触发
         */
        fun onNetworkRestored() {}
    }

    /**
     * 网络类型枚举
     */
    enum class NetworkType {
        NONE,           // 无网络
        WIFI,           // WiFi网络
        MOBILE,         // 移动网络
        ETHERNET,       // 以太网
        VPN,            // VPN网络
        UNKNOWN         // 未知网络类型
    }

    /**
     * 网络回调包装类
     */
    private inner class NetworkCallback : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            super.onAvailable(network)
            val networkType = getNetworkType(network)
            val isConnected = networkType != NetworkType.NONE

            Log.d(TAG, "Network connected: $networkType")

            // 通知所有监听器
            networkStateListeners.forEach { listener ->
                listener.onNetworkStateChanged(isConnected, networkType)
                if (isConnected) {
                    listener.onNetworkRestored()
                }
            }
        }

        override fun onLost(network: Network) {
            super.onLost(network)
            Log.d(TAG, "Network disconnected")

            // 通知所有监听器
            networkStateListeners.forEach { listener ->
                listener.onNetworkStateChanged(false, NetworkType.NONE)
            }
        }

        override fun onCapabilitiesChanged(
            network: Network,
            networkCapabilities: NetworkCapabilities,
        ) {
            super.onCapabilitiesChanged(network, networkCapabilities)
            val networkType = getNetworkType(network)
            Log.d(TAG, "Network capabilities changed: $networkType")
        }
    }

    /**
     * 初始化网络管理器
     * @param context 应用上下文
     */
    fun initialize(context: Context) {
        if (applicationContext == null) {
            applicationContext = context.applicationContext
            connectivityManager = applicationContext?.getSystemService<ConnectivityManager>()
            registerNetworkCallback()
        }
    }

    /**
     * 注册网络回调
     */
    private fun registerNetworkCallback() {
        val networkRequest = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()

        val callback = NetworkCallback()
        networkCallbacks.add(callback)
        connectivityManager?.registerNetworkCallback(networkRequest, callback)
    }

    /**
     * 判断当前是否有网络连接
     * @return true 表示有网络连接，false 表示无网络连接
     */
    fun isNetworkConnected(): Boolean {
        val network = connectivityManager?.activeNetwork
        val capabilities = connectivityManager?.getNetworkCapabilities(network)
        return capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true
    }

    /**
     * 获取当前网络类型
     * @return 网络类型枚举
     */
    fun getCurrentNetworkType(): NetworkType {
        val network = connectivityManager?.activeNetwork
        return if (network != null) {
            getNetworkType(network)
        } else {
            NetworkType.NONE
        }
    }

    /**
     * 获取指定网络的类型
     * @param network 网络对象
     * @return 网络类型枚举
     */
    private fun getNetworkType(network: Network): NetworkType {
        val capabilities = connectivityManager?.getNetworkCapabilities(network)
        return when {
            capabilities == null -> NetworkType.NONE
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> NetworkType.WIFI
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> NetworkType.MOBILE
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> NetworkType.ETHERNET
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN) -> NetworkType.VPN
            else -> NetworkType.UNKNOWN
        }
    }

    /**
     * 添加网络状态监听器
     * @param listener 网络状态监听器
     */
    fun addNetworkStateListener(listener: NetworkStateListener) {
        if (!networkStateListeners.contains(listener)) {
            networkStateListeners.add(listener)
            // 立即通知当前网络状态
            val isConnected = isNetworkConnected()
            val networkType = getCurrentNetworkType()
            listener.onNetworkStateChanged(isConnected, networkType)
        }
    }

    /**
     * 移除网络状态监听器
     * @param listener 网络状态监听器
     */
    fun removeNetworkStateListener(listener: NetworkStateListener) {
        networkStateListeners.remove(listener)
    }

    /**
     * 获取网络状态变化流
     * @return 网络状态变化的 Flow
     */
    fun getNetworkStateFlow(): Flow<NetworkState> = callbackFlow {
        val listener = object : NetworkStateListener {
            override fun onNetworkStateChanged(isConnected: Boolean, networkType: NetworkType) {
                trySend(NetworkState(isConnected, networkType))
            }
        }

        addNetworkStateListener(listener)

        awaitClose {
            removeNetworkStateListener(listener)
        }
    }.distinctUntilChanged()

    /**
     * 网络状态数据类
     */
    data class NetworkState(
        val isConnected: Boolean,
        val networkType: NetworkType,
    )

    /**
     * 检查是否应该显示网络错误提示
     * 当网络未连接时，不显示网络相关的错误提示
     * @return true 表示应该显示错误提示，false 表示不应该显示
     */
    fun shouldShowNetworkError(): Boolean {
        return isNetworkConnected()
    }

    /**
     * 获取网络错误提示信息
     * 根据网络状态返回合适的错误信息
     * @param originalMessage 原始错误信息
     * @return 处理后的错误信息
     */
    fun getNetworkErrorMessage(originalMessage: String): String {
        return if (isNetworkConnected()) {
            originalMessage
        } else {
            "Network connection unavailable, please check your network settings"
        }
    }

    /**
     * 释放资源
     */
    fun release() {
        try {
            // 注销网络回调
            networkCallbacks.forEach { callback ->
                connectivityManager?.unregisterNetworkCallback(callback)
            }
            networkCallbacks.clear()

            // 清空监听器列表
            networkStateListeners.clear()

            // 清空引用
            connectivityManager = null
            applicationContext = null
            INSTANCE = null
        } catch (e: Exception) {
            Log.e(TAG, "Failed to release network manager resources: ${e.message}")
        }
    }
}