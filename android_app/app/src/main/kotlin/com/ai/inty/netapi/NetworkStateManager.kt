package com.ai.inty.netapi

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import com.inty.utils.log.EasyLog
import java.util.concurrent.CopyOnWriteArrayList

/**
 * 网络状态管理器
 * 提供统一的网络状态监控和管理
 */
object NetworkStateManager {

    private var connectivityManager: ConnectivityManager? = null
    private var applicationContext: Context? = null
    private val networkCallbacks = CopyOnWriteArrayList<ConnectivityManager.NetworkCallback>()

    /**
     * 网络类型枚举
     */
    enum class NetworkType {
        NONE, WIFI, MOBILE, ETHERNET, VPN, UNKNOWN
    }

    /**
     * 网络状态数据类
     */
    data class NetworkState(
        val isConnected: Boolean,
        val networkType: NetworkType,
        val timestamp: Long = System.currentTimeMillis()
    )

    /**
     * 初始化网络状态管理器
     */
    fun initialize(context: Context) {
        if (applicationContext == null) {
            applicationContext = context.applicationContext
            connectivityManager =
                applicationContext?.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            registerNetworkCallback()
            EasyLog.log("NetworkStateManager initialized")
        }
    }

    /**
     * 注册网络回调
     */
    private fun registerNetworkCallback() {
        val networkRequest = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .build()

        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                super.onAvailable(network)
                val networkType = getNetworkType(network)
                EasyLog.log("Network connected: $networkType")
            }

            override fun onLost(network: Network) {
                super.onLost(network)
                EasyLog.log("Network disconnected")
            }

            override fun onCapabilitiesChanged(
                network: Network,
                networkCapabilities: NetworkCapabilities
            ) {
                super.onCapabilitiesChanged(network, networkCapabilities)
                val networkType = getNetworkType(network)
                EasyLog.log("Network capabilities changed: $networkType")
            }
        }

        networkCallbacks.add(callback)
        connectivityManager?.registerNetworkCallback(networkRequest, callback)
    }


    /**
     * 获取指定网络的类型
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
     * 检查网络是否连接
     */
    fun isNetworkConnected(): Boolean {
        val network = connectivityManager?.activeNetwork
        val capabilities = connectivityManager?.getNetworkCapabilities(network)
        return capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true
    }

    /**
     * 获取当前网络类型
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
     * 获取当前网络状态
     */
    fun getCurrentNetworkState(): NetworkState {
        val isConnected = isNetworkConnected()
        val networkType = getCurrentNetworkType()
        return NetworkState(isConnected, networkType)
    }


    /**
     * 释放资源
     */
    fun release() {
        try {
            networkCallbacks.forEach { callback ->
                connectivityManager?.unregisterNetworkCallback(callback)
            }
            networkCallbacks.clear()
            connectivityManager = null
            applicationContext = null
            EasyLog.log("NetworkStateManager released")
        } catch (e: Exception) {
            EasyLog.log("Failed to release NetworkStateManager: ${e.message}", EasyLog.ERROR)
        }
    }
}
