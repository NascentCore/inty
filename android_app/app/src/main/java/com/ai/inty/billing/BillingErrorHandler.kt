package com.ai.inty.billing

import android.content.Context
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingResult
import com.inty.utils.log.EasyLog

/**
 * Billing错误处理工具类
 * 统一处理各种billing错误情况
 */
object BillingErrorHandler {

    /**
     * 处理BillingResult错误
     */
    fun handleBillingError(billingResult: BillingResult, context: Context? = null) {
        val errorMessage = when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                "计费不可用: 设备不支持 Google Play 计费"
            }

            BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                "开发者错误: 请检查商品ID配置、应用签名、测试用户设置"
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                "服务不可用: Google Play 服务暂时不可用"
            }

            BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                "网络错误: 请检查网络连接"
            }

            BillingClient.BillingResponseCode.USER_CANCELED -> {
                "用户取消: 用户取消了购买操作"
            }

            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                "商品已拥有: 用户已经拥有此商品"
            }

            BillingClient.BillingResponseCode.ITEM_NOT_OWNED -> {
                "商品未拥有: 用户未拥有此商品"
            }

            BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                "商品不可用: 商品在当前地区不可用"
            }

            BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                "功能不支持: 当前设备不支持此功能"
            }

            BillingClient.BillingResponseCode.SERVICE_DISCONNECTED -> {
                "服务断开: Google Play 服务连接断开"
            }

            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                "商品已拥有: 用户已经拥有此商品"
            }

            else -> {
                "未知错误: 响应码 ${billingResult.responseCode}, ${billingResult.debugMessage}"
            }
        }

        EasyLog.log("BillingErrorHandler - $errorMessage", EasyLog.ERROR)

        // 记录详细错误信息
        EasyLog.log("BillingErrorHandler - 详细错误信息: ${billingResult.debugMessage}")
        EasyLog.log("BillingErrorHandler - 错误响应码: ${billingResult.responseCode}")
    }

    /**
     * 处理价格查询错误
     */
    fun handlePriceQueryError(billingResult: BillingResult) {
        val errorMessage = when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                "价格查询失败: 计费不可用，设备不支持 Google Play 计费"
            }

            BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                "价格查询失败: 开发者错误，请检查商品ID配置"
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                "价格查询失败: Google Play 服务暂时不可用"
            }

            BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                "价格查询失败: 网络连接错误"
            }

            else -> {
                "价格查询失败: 响应码 ${billingResult.responseCode}, ${billingResult.debugMessage}"
            }
        }

        EasyLog.log("BillingErrorHandler - $errorMessage", EasyLog.ERROR)
    }

    /**
     * 处理购买错误
     */
    fun handlePurchaseError(billingResult: BillingResult) {
        val errorMessage = when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                "购买失败: 计费不可用，设备不支持 Google Play 计费"
            }

            BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                "购买失败: 开发者错误，请检查应用配置"
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                "购买失败: Google Play 服务暂时不可用"
            }

            BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                "购买失败: 网络连接错误"
            }

            BillingClient.BillingResponseCode.USER_CANCELED -> {
                "购买取消: 用户取消了购买操作"
            }

            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                "购买失败: 用户已经拥有此商品"
            }

            BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                "购买失败: 商品在当前地区不可用"
            }

            BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                "购买失败: 当前设备不支持此功能"
            }

            else -> {
                "购买失败: 响应码 ${billingResult.responseCode}, ${billingResult.debugMessage}"
            }
        }

        EasyLog.log("BillingErrorHandler - $errorMessage", EasyLog.ERROR)
    }

    /**
     * 处理连接错误
     */
    fun handleConnectionError(billingResult: BillingResult) {
        val errorMessage = when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                "连接失败: 计费不可用，设备不支持 Google Play 计费"
            }

            BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                "连接失败: 开发者错误，请检查应用签名和配置"
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                "连接失败: Google Play 服务暂时不可用"
            }

            BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                "连接失败: 网络连接错误"
            }

            BillingClient.BillingResponseCode.SERVICE_DISCONNECTED -> {
                "连接断开: Google Play 服务连接断开"
            }

            else -> {
                "连接失败: 响应码 ${billingResult.responseCode}, ${billingResult.debugMessage}"
            }
        }

        EasyLog.log("BillingErrorHandler - $errorMessage", EasyLog.ERROR)
    }

    /**
     * 获取用户友好的错误信息
     */
    fun getUserFriendlyErrorMessage(billingResult: BillingResult): String {
        return when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                "设备不支持 Google Play 计费，请确保设备已安装 Google Play 商店"
            }

            BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                "应用配置错误，请联系开发者"
            }

            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                "Google Play 服务暂时不可用，请稍后重试"
            }

            BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                "网络连接错误，请检查网络设置"
            }

            BillingClient.BillingResponseCode.USER_CANCELED -> {
                "购买已取消"
            }

            BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                "您已经拥有此商品"
            }

            BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                "此商品在当前地区不可用"
            }

            BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                "当前设备不支持此功能"
            }

            else -> {
                "发生未知错误，请稍后重试"
            }
        }
    }

    /**
     * 检查是否为可恢复的错误
     */
    fun isRecoverableError(billingResult: BillingResult): Boolean {
        return when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE,
            BillingClient.BillingResponseCode.NETWORK_ERROR,
            BillingClient.BillingResponseCode.SERVICE_DISCONNECTED -> true

            else -> false
        }
    }

    /**
     * 检查是否需要重试
     */
    fun shouldRetry(billingResult: BillingResult): Boolean {
        return when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE,
            BillingClient.BillingResponseCode.NETWORK_ERROR,
            BillingClient.BillingResponseCode.SERVICE_DISCONNECTED -> true

            else -> false
        }
    }
}
