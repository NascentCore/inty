package com.ai.inty.billing

import ai.sxwl.android.utils.LogUtils
import android.content.Context
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingResult

/** Billing错误处理工具类 统一处理各种billing错误情况 */
object BillingErrorHandler {

    /** 错误类型枚举 */
    enum class ErrorType {
        PRICE_QUERY,
        PURCHASE,
        CONNECTION,
        GENERAL,
    }

    /** 处理价格查询错误 */
    fun handlePriceQueryError(billingResult: BillingResult) {
        handleBillingError(billingResult, errorType = ErrorType.PRICE_QUERY)
    }

    /** 统一的错误处理方法 */
    private fun handleBillingError(
        billingResult: BillingResult,
        context: Context? = null,
        errorType: ErrorType = ErrorType.GENERAL,
    ) {
        val errorMessage = getErrorMessage(billingResult, errorType)
        LogUtils.e("BillingErrorHandler - $errorMessage")

        // 记录详细错误信息
        LogUtils.i("BillingErrorHandler - 详细错误信息: ${billingResult.debugMessage}")
        LogUtils.i("BillingErrorHandler - 错误响应码: ${billingResult.responseCode}")

        // 提供解决建议
        provideSolutionSuggestions(billingResult, context)
    }

    /** 获取错误信息 */
    private fun getErrorMessage(billingResult: BillingResult, errorType: ErrorType): String {
        val prefix =
            when (errorType) {
                ErrorType.PRICE_QUERY -> "价格查询失败: "
                ErrorType.PURCHASE -> "购买失败: "
                ErrorType.CONNECTION -> "连接失败: "
                ErrorType.GENERAL -> ""
            }

        val message =
            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    "计费不可用，设备不支持 Google Play 计费"
                }

                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    "开发者错误，请检查商品ID配置、应用签名、测试用户设置"
                }

                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    "Google Play 服务暂时不可用"
                }

                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    "网络连接错误"
                }

                BillingClient.BillingResponseCode.USER_CANCELED -> {
                    "用户取消了操作"
                }

                BillingClient.BillingResponseCode.ITEM_ALREADY_OWNED -> {
                    "用户已经拥有此商品"
                }

                BillingClient.BillingResponseCode.ITEM_NOT_OWNED -> {
                    "用户未拥有此商品"
                }

                BillingClient.BillingResponseCode.ITEM_UNAVAILABLE -> {
                    "商品在当前地区不可用"
                }

                BillingClient.BillingResponseCode.FEATURE_NOT_SUPPORTED -> {
                    "当前设备不支持此功能"
                }

                BillingClient.BillingResponseCode.SERVICE_DISCONNECTED -> {
                    "Google Play 服务连接断开"
                }

                else -> {
                    "未知错误，响应码 ${billingResult.responseCode}, ${billingResult.debugMessage}"
                }
            }

        return prefix + message
    }

    /** 提供解决建议 */
    private fun provideSolutionSuggestions(billingResult: BillingResult, context: Context?) {
        val suggestions =
            when (billingResult.responseCode) {
                BillingClient.BillingResponseCode.BILLING_UNAVAILABLE -> {
                    listOf(
                        "1. 检查设备是否安装了Google Play服务",
                        "2. 确认设备是否支持Google Play计费",
                        "3. 尝试重启应用或设备",
                        "4. 检查设备是否在支持的地区",
                        "5. 确认Google账户是否正常",
                    )
                }

                BillingClient.BillingResponseCode.SERVICE_UNAVAILABLE -> {
                    listOf(
                        "1. 检查网络连接是否正常",
                        "2. 等待几分钟后重试",
                        "3. 检查Google Play服务是否正在更新",
                        "4. 尝试清除Google Play服务缓存",
                        "5. 重启设备",
                    )
                }

                BillingClient.BillingResponseCode.NETWORK_ERROR -> {
                    listOf("1. 检查网络连接", "2. 尝试切换WiFi/移动网络", "3. 检查防火墙设置", "4. 等待网络稳定后重试")
                }

                BillingClient.BillingResponseCode.DEVELOPER_ERROR -> {
                    listOf("1. 检查商品ID配置是否正确", "2. 确认应用签名是否匹配", "3. 检查测试用户设置", "4. 联系开发者支持")
                }

                else -> {
                    listOf("1. 尝试重启应用", "2. 检查设备状态", "3. 等待一段时间后重试", "4. 联系客服支持")
                }
            }

        LogUtils.i("BillingErrorHandler - 解决建议:")
        suggestions.forEach { suggestion -> LogUtils.i("BillingErrorHandler - $suggestion") }

    }
}
