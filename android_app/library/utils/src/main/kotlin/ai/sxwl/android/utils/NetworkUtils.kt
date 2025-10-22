package ai.sxwl.android.utils

import android.Manifest
import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.os.Build
import androidx.annotation.RequiresPermission
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.distinctUntilChanged

/**
 * 网络工具类
 * 提供网络相关的工具方法，支持复杂网络场景检测
 */
object NetworkUtils {

    private const val TAG = "NetworkUtils"

    // ==================== 网络类型枚举 ====================

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
     * 网络状态数据类
     */
    data class NetworkState(
        val isConnected: Boolean,
        val networkType: NetworkType,
        val isMetered: Boolean = false,
        val isRoaming: Boolean = false
    )

    // ==================== 基础网络检测 ====================

    /**
     * 检查网络是否连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isConnected(): Boolean = isConnected(Utils.getApp())

    /**
     * 检查网络是否连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isConnected(context: Context?): Boolean {
        if (context == null) return false
        return isNetworkActuallyAvailable(context)
    }

    /**
     * 检查网络是否真正可用（排除飞行模式下的VPN连接等虚假连接）
     * 通过检查网络传输类型来判断是否为真实网络连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    private fun isNetworkActuallyAvailable(context: Context): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(network) ?: return false

            // 检查是否有互联网能力
            if (!capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)) {
                return false
            }

            // 检查是否有有效的传输类型（排除仅VPN连接的情况）
            val hasValidTransport = capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                    capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) ||
                    capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)

            // 如果只有VPN传输，检查是否在飞行模式下
            val hasOnlyVpn = capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN) &&
                    !capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) &&
                    !capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) &&
                    !capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)

            if (hasOnlyVpn) {
                // 如果只有VPN连接，检查是否在飞行模式下
                // 在飞行模式下，即使VPN显示连接，实际上也无法访问互联网
                return false
            }

            hasValidTransport
        } else {
            @Suppress("DEPRECATION")
            cm.activeNetworkInfo?.isConnected == true
        }
    }

    // ==================== 网络类型检测 ====================

    /**
     * 检查是否为WiFi连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isWifiConnected(): Boolean = isWifiConnected(Utils.getApp())

    /**
     * 检查是否为WiFi连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isWifiConnected(context: Context?): Boolean {
        if (context == null) return false
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(network) ?: return false
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
        } else {
            @Suppress("DEPRECATION")
            cm.getNetworkInfo(ConnectivityManager.TYPE_WIFI)?.isConnected == true
        }
    }

    /**
     * 检查是否为移动网络连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isMobileConnected(): Boolean = isMobileConnected(Utils.getApp())

    /**
     * 检查是否为移动网络连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isMobileConnected(context: Context?): Boolean {
        if (context == null) return false
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(network) ?: return false
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)
        } else {
            @Suppress("DEPRECATION")
            cm.getNetworkInfo(ConnectivityManager.TYPE_MOBILE)?.isConnected == true
        }
    }

    /**
     * 检查是否为以太网连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isEthernetConnected(context: Context? = Utils.getApp()): Boolean {
        if (context == null) return false
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(network) ?: return false
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
        } else {
            false // 低版本不支持以太网检测
        }
    }

    /**
     * 检查是否为VPN连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isVpnConnected(context: Context? = Utils.getApp()): Boolean {
        if (context == null) return false
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(network) ?: return false
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN)
        } else {
            false // 低版本不支持VPN检测
        }
    }

    // ==================== 网络状态检测 ====================

    /**
     * 检查是否为移动数据流量
     * 用于判断网络拦截数据使用的是手机流量
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isMobileData(): Boolean = isMobileData(Utils.getApp())

    /**
     * 检查是否为移动数据流量
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isMobileData(context: Context?): Boolean {
        if (context == null) return false
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(network) ?: return false
            // 检查是否为移动网络且不是计费网络（即使用移动数据流量）
            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) &&
                    !capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED)
        } else {
            @Suppress("DEPRECATION")
            val mobileInfo = cm.getNetworkInfo(ConnectivityManager.TYPE_MOBILE)
            mobileInfo?.isConnected == true && !mobileInfo.isRoaming
        }
    }

    /**
     * 检查是否为计费网络
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isMeteredNetwork(context: Context? = Utils.getApp()): Boolean {
        if (context == null) return false
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(network) ?: return false
            !capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED)
        } else {
            @Suppress("DEPRECATION")
            cm.isActiveNetworkMetered
        }
    }

    /**
     * 检查是否为漫游网络
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isRoamingNetwork(context: Context? = Utils.getApp()): Boolean {
        if (context == null) return false
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(network) ?: return false
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_ROAMING)
        } else {
            @Suppress("DEPRECATION")
            cm.activeNetworkInfo?.isRoaming == true
        }
    }

    // ==================== 网络类型获取 ====================

    /**
     * 获取当前网络类型
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun getCurrentNetworkType(context: Context? = Utils.getApp()): NetworkType {
        if (context == null) return NetworkType.NONE
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return NetworkType.NONE

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return NetworkType.NONE
            getNetworkTypeFromCapabilities(cm.getNetworkCapabilities(network))
        } else {
            @Suppress("DEPRECATION")
            val networkInfo = cm.activeNetworkInfo
            when {
                networkInfo?.isConnected != true -> NetworkType.NONE
                networkInfo.type == ConnectivityManager.TYPE_WIFI -> NetworkType.WIFI
                networkInfo.type == ConnectivityManager.TYPE_MOBILE -> NetworkType.MOBILE
                networkInfo.type == ConnectivityManager.TYPE_ETHERNET -> NetworkType.ETHERNET
                else -> NetworkType.UNKNOWN
            }
        }
    }

    /**
     * 从网络能力获取网络类型
     */
    private fun getNetworkTypeFromCapabilities(capabilities: NetworkCapabilities?): NetworkType {
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
     * 获取网络类型字符串
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun getNetworkTypeString(context: Context? = Utils.getApp()): String {
        return when (getCurrentNetworkType(context)) {
            NetworkType.NONE -> "无网络"
            NetworkType.WIFI -> "WiFi"
            NetworkType.MOBILE -> "移动网络"
            NetworkType.ETHERNET -> "以太网"
            NetworkType.VPN -> "VPN"
            NetworkType.UNKNOWN -> "未知网络"
        }
    }

    // ==================== 网络状态获取 ====================

    /**
     * 获取完整的网络状态
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun getNetworkState(context: Context? = Utils.getApp()): NetworkState {
        if (context == null) return NetworkState(false, NetworkType.NONE)

        val isConnected = isConnected(context)
        val networkType = getCurrentNetworkType(context)
        val isMetered = isMeteredNetwork(context)
        val isRoaming = isRoamingNetwork(context)

        return NetworkState(isConnected, networkType, isMetered, isRoaming)
    }

    // ==================== 网络状态监听 ====================

    /**
     * 网络状态监听器接口
     */
    interface NetworkStateListener {
        /**
         * 网络状态变化回调
         * @param networkState 网络状态
         */
        fun onNetworkStateChanged(networkState: NetworkState)

        /**
         * 网络恢复回调
         */
        fun onNetworkRestored() {}
    }

    /**
     * 获取网络状态变化流
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun getNetworkStateFlow(context: Context? = Utils.getApp()): Flow<NetworkState> {
        if (context == null) return callbackFlow { close() }

        return callbackFlow {
            val listener = object : NetworkStateListener {
                override fun onNetworkStateChanged(networkState: NetworkState) {
                    trySend(networkState)
                }
            }

            // 注册网络回调
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            val networkRequest = NetworkRequest.Builder()
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .build()

            val callback = object : ConnectivityManager.NetworkCallback() {
                @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
                override fun onAvailable(network: Network) {
                    super.onAvailable(network)
                    val networkState = getNetworkState(context)
                    listener.onNetworkStateChanged(networkState)
                    if (networkState.isConnected) {
                        listener.onNetworkRestored()
                    }
                }

                override fun onLost(network: Network) {
                    super.onLost(network)
                    listener.onNetworkStateChanged(NetworkState(false, NetworkType.NONE))
                }
            }

            cm?.registerNetworkCallback(networkRequest, callback)

            // 立即发送当前网络状态
            trySend(getNetworkState(context))

            awaitClose {
                cm?.unregisterNetworkCallback(callback)
            }
        }.distinctUntilChanged()
    }

    // ==================== 便捷方法 ====================

    /**
     * 检查是否应该显示网络错误提示
     * 当网络未连接时，不显示网络相关的错误提示
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun shouldShowNetworkError(context: Context? = Utils.getApp()): Boolean {
        return isConnected(context)
    }

    /**
     * 检查是否为高质量网络连接
     */
    @RequiresPermission(Manifest.permission.ACCESS_NETWORK_STATE)
    fun isHighQualityNetwork(context: Context? = Utils.getApp()): Boolean {
        if (context == null) return false
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return false

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = cm.activeNetwork ?: return false
            val capabilities = cm.getNetworkCapabilities(network) ?: return false

            // 检查是否有高质量网络能力
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                    (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET))
        } else {
            isWifiConnected(context) || isEthernetConnected(context)
        }
    }
}
